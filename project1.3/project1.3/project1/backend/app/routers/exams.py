from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models.exam import Exam, ExamQuestion
from ..models.question import Question
from ..schemas.exam import ExamRequirements
from ..services.exam_generator import ExamGenerator, _normalize_scores
from ..services.docx_export import export_exam_to_docx
from ..services.exam_export import export_exam_to_pdf, export_exam_to_txt
from ..services.answer_sheet import generate_answer_sheet_pdf

router = APIRouter(prefix="/exams", tags=["exams"])


@router.post("/generate")
async def generate_exam(req: ExamRequirements, db: AsyncSession = Depends(get_db)):
    """Generate an exam based on requirements."""
    generator = ExamGenerator(db)
    result = await generator.generate(req.model_dump())

    questions = result.get("questions", [])
    if not questions:
        raise HTTPException(status_code=400, detail="Failed to generate any questions")

    # Normalize scores to ensure sum matches total_score exactly
    questions = _normalize_scores(questions, req.total_score)

    exam = Exam(
        title=req.title,
        created_by="teacher",
        total_score=req.total_score,
        duration=req.duration,
        requirements_json=req.model_dump(),
        status="draft",
    )
    db.add(exam)
    await db.flush()

    for idx, q in enumerate(questions):
        question_id = q.get("question_id")
        score = q["score"]  # Already normalized
        if question_id:
            eq = ExamQuestion(
                exam_id=exam.id,
                question_id=question_id,
                score=score,
                sort_order=idx,
            )
            db.add(eq)

    await db.commit()
    await db.refresh(exam)
    return {"exam_id": exam.id, "question_count": len(questions)}


@router.get("")
async def list_exams(db: AsyncSession = Depends(get_db)):
    """List all generated exams."""
    result = await db.execute(
        select(Exam).order_by(Exam.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{exam_id}")
async def get_exam(exam_id: int, db: AsyncSession = Depends(get_db)):
    """Get exam with all questions."""
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    await db.refresh(exam, ["questions"])
    result = {
        "id": exam.id,
        "title": exam.title,
        "status": exam.status,
        "total_score": exam.total_score,
        "duration": exam.duration,
        "created_at": str(exam.created_at),
        "questions": [],
    }
    for eq in sorted(exam.questions, key=lambda x: x.sort_order):
        q = await db.get(Question, eq.question_id)
        result["questions"].append({
            "eq_id": eq.id,
            "question_id": q.id if q else None,
            "score": eq.score,
            "sort_order": eq.sort_order,
            "type": q.type if q else "",
            "content": q.content if q else "（题目已删除）",
            "options": q.options if q else None,
            "answer": q.answer if q else "",
            "explanation": q.explanation if q else "",
        })
    return result


@router.put("/{exam_id}/questions/{eq_id}")
async def replace_question(
    exam_id: int, eq_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Replace or edit a question in the exam."""
    eq = await db.get(ExamQuestion, eq_id)
    if not eq or eq.exam_id != exam_id:
        raise HTTPException(status_code=404, detail="Question not found in exam")

    if data.get("question_id"):  # Swap with another bank question
        eq.question_id = data["question_id"]

    # Manual content edit
    if any(k in data for k in ("content", "type", "answer", "options", "explanation")):
        q = await db.get(Question, eq.question_id)
        if q:
            if "content" in data:
                q.content = data["content"]
            if "type" in data:
                q.type = data["type"]
            if "answer" in data:
                q.answer = data["answer"]
            if "options" in data:
                q.options = data["options"]
            if "explanation" in data:
                q.explanation = data["explanation"]

    # Score change
    if data.get("score") is not None:
        eq.score = data["score"]

    # Sort order change (move up/down)
    if data.get("sort_order") is not None:
        eq.sort_order = data["sort_order"]

    await db.commit()
    return {"status": "ok"}


@router.post("/{exam_id}/questions/{eq_id}/regenerate")
async def regenerate_question(
    exam_id: int, eq_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Regenerate a single question in the exam — picks a new one of same type."""
    eq = await db.get(ExamQuestion, eq_id)
    if not eq or eq.exam_id != exam_id:
        raise HTTPException(status_code=404, detail="Question not found in exam")

    old_q = await db.get(Question, eq.question_id)
    if not old_q:
        raise HTTPException(status_code=404, detail="Original question not found")

    # RAG search for a different question of same type
    from ..services.rag import RAGPipeline
    from ..services.llm_adapter import LLMAdapter
    llm = LLMAdapter()
    rag = RAGPipeline()
    query_embedding = await llm.embed(old_q.content[:500])
    where = {"type": old_q.type}
    results = rag.search(query_embedding, top_k=10, where=where)

    # Pick the first one that's different from the current
    new_id = None
    for r in results:
        if r["id"] != old_q.id:
            new_id = r["id"]
            break

    if not new_id:
        raise HTTPException(status_code=404, detail="No alternative question found")

    eq.question_id = new_id
    await db.commit()
    return {"status": "ok", "new_question_id": new_id}


@router.get("/{exam_id}/export")
async def export_exam(
    exam_id: int,
    format: str = "docx",
    with_answer: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Export exam as DOCX / PDF / TXT file."""
    exam_row = (await db.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if not exam_row:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Load questions
    eq_rows = (await db.execute(
        select(ExamQuestion).where(ExamQuestion.exam_id == exam_id).order_by(ExamQuestion.sort_order)
    )).scalars().all()

    questions = []
    for eq in eq_rows:
        q = (await db.execute(select(Question).where(Question.id == eq.question_id))).scalar_one_or_none()
        if q:
            questions.append({
                "type": q.type,
                "score": eq.score,
                "question": {
                    "content": q.content,
                    "options": q.options,
                    "answer": q.answer,
                    "explanation": q.explanation,
                },
            })

    exam_data = {
        "title": exam_row.title,
        "total_score": exam_row.total_score,
        "duration": exam_row.duration,
        "questions": questions,
    }

    if format == "docx":
        content = export_exam_to_docx(exam_data, with_answer=with_answer).getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif format == "pdf":
        content = export_exam_to_pdf(exam_data, with_answer=with_answer).getvalue()
        media_type = "application/pdf"
    elif format == "txt":
        # utf-8-sig BOM so Windows Notepad detects the encoding
        content = export_exam_to_txt(exam_data, with_answer=with_answer).encode("utf-8-sig")
        media_type = "text/plain; charset=utf-8"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    # HTTP headers are latin-1 only — Chinese filename must use RFC 5987 filename*
    filename = f"{exam_row.title}.{format}".replace(" ", "_")
    ascii_fallback = f"exam_{exam_id}.{format}"
    return Response(
        content,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_fallback}"; '
                f"filename*=UTF-8''{quote(filename)}"
            )
        },
    )


EVALUATE_SYSTEM_PROMPT = """你是《数据结构》课程的试卷质量评审专家。请对给定试卷进行专业评价。

输出 JSON（不要输出其他内容）:
{
  "total_rating": 85,
  "comment": "总体评语（2-3句话）",
  "knowledge_coverage": "知识点覆盖分析",
  "focus_analysis": "考察重点分析",
  "type_distribution_review": "题型与分值分布评价",
  "suggestions": "改进建议"
}

规则:
1. total_rating 为 0-100 的整数，综合考虑知识覆盖、难度梯度、题型搭配、分值分配
2. 评价要具体、专业，指出实际的优点和不足
3. 严格输出合法 JSON"""


@router.post("/{exam_id}/evaluate")
async def evaluate_exam(exam_id: int, db: AsyncSession = Depends(get_db)):
    """AI evaluation of exam quality — coverage, difficulty, distribution."""
    exam_row = (await db.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if not exam_row:
        raise HTTPException(status_code=404, detail="Exam not found")

    eq_rows = (await db.execute(
        select(ExamQuestion).where(ExamQuestion.exam_id == exam_id).order_by(ExamQuestion.sort_order)
    )).scalars().all()

    q_lines = []
    for idx, eq in enumerate(eq_rows, 1):
        q = (await db.execute(select(Question).where(Question.id == eq.question_id))).scalar_one_or_none()
        if q:
            q_lines.append(
                f"{idx}. [{q.type}] [难度{q.difficulty}] [{q.chapter or '未知章节'}] "
                f"({eq.score}分) {q.content[:150]}"
            )
    if not q_lines:
        raise HTTPException(status_code=400, detail="试卷没有题目，无法评价")

    user_prompt = f"""试卷标题: {exam_row.title}
总分: {exam_row.total_score}分 | 时长: {exam_row.duration}分钟 | 共{len(q_lines)}题

题目清单:
{chr(10).join(q_lines)}

请评价这份试卷。"""

    from ..services.llm_adapter import LLMAdapter
    llm = LLMAdapter()
    try:
        result = await llm.chat(EVALUATE_SYSTEM_PROMPT, user_prompt)
        data = llm._parse_json(result)
        if not isinstance(data, dict):
            raise ValueError("unexpected response shape")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 评价失败: {e}")
    return data


@router.post("/{exam_id}/verify")
async def verify_exam(
    exam_id: int,
    auto_fix: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """二次审核：校验总分、题量、题型是否与组卷要求一致。auto_fix=true 时自动修复。"""
    exam_row = (await db.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if not exam_row:
        raise HTTPException(status_code=404, detail="Exam not found")

    eq_rows = (await db.execute(
        select(ExamQuestion).where(ExamQuestion.exam_id == exam_id).order_by(ExamQuestion.sort_order)
    )).scalars().all()

    if not eq_rows:
        raise HTTPException(status_code=400, detail="Exam has no questions")

    # Calculate actual values
    actual_total_score = 0
    actual_type_counts = {}
    for eq in eq_rows:
        actual_total_score += eq.score
        q = (await db.execute(select(Question).where(Question.id == eq.question_id))).scalar_one_or_none()
        if q:
            actual_type_counts[q.type] = actual_type_counts.get(q.type, 0) + 1

    requirements = exam_row.requirements_json or {}
    expected_total = exam_row.total_score
    expected_dist = requirements.get("question_distribution", {})
    expected_count = sum(expected_dist.values())

    score_match = actual_total_score == expected_total
    actual_count = len(eq_rows)
    count_match = actual_count == expected_count if expected_count else True

    type_names = {"choice": "选择题", "fill": "填空题", "tf": "判断题", "short_answer": "简答题", "code": "算法设计题"}
    type_ok = True
    type_details = []
    for qtype, expected_n in expected_dist.items():
        actual_n = actual_type_counts.get(qtype, 0)
        if expected_n > 0 and actual_n != expected_n:
            type_ok = False
            type_details.append(f"{type_names.get(qtype, qtype)}实际{actual_n}题，要求{expected_n}题")

    all_passed = score_match and count_match and type_ok

    # ── Auto-fix if requested and not passed ──
    fix_log = []
    if auto_fix and not all_passed:
        from ..services.rag import RAGPipeline
        from ..services.llm_adapter import LLMAdapter
        llm = LLMAdapter()
        rag = RAGPipeline()

        # 1. Fix score: re-normalize
        if not score_match and eq_rows:
            base = expected_total // len(eq_rows)
            remainder = expected_total - base * len(eq_rows)
            for i, eq in enumerate(eq_rows):
                eq.score = base + (1 if i < remainder else 0)
            fix_log.append(f"分数已重新分配：每题{base}分基础" + (f"，前{remainder}题+1分" if remainder else ""))

        # 2. Fix count/type: remove excess, add missing
        if not count_match or not type_ok:
            # Remove excess questions for types with too many
            type_counters = {}
            to_remove = []
            for eq in eq_rows:
                q = (await db.execute(select(Question).where(Question.id == eq.question_id))).scalar_one_or_none()
                qtype = q.type if q else ""
                expected = expected_dist.get(qtype, 0)
                current = type_counters.get(qtype, 0)
                if expected > 0 and current >= expected:
                    to_remove.append(eq)
                else:
                    type_counters[qtype] = current + 1

            for eq in to_remove:
                await db.delete(eq)
                eq_rows.remove(eq)
            if to_remove:
                fix_log.append(f"移除了{len(to_remove)}道多余题目")

            # Add missing questions for types with shortfall
            for qtype, expected in expected_dist.items():
                if expected == 0:
                    continue
                current = type_counters.get(qtype, 0)
                shortfall = expected - current
                if shortfall <= 0:
                    continue

                # RAG search for more questions
                knowledge_context = requirements.get("scope", "")
                if not knowledge_context:
                    knowledge_context = requirements.get("title", "")
                query_embedding = await llm.embed(knowledge_context[:500])
                where = {"type": qtype}
                results = rag.search(query_embedding, top_k=shortfall * 3, where=where)

                # Exclude already-used question IDs
                used_ids = {eq.question_id for eq in eq_rows}
                added = 0
                max_sort = max((eq.sort_order for eq in eq_rows), default=0)
                for r in results:
                    if added >= shortfall:
                        break
                    if r["id"] in used_ids:
                        continue
                    eq = ExamQuestion(
                        exam_id=exam_id,
                        question_id=r["id"],
                        score=1,  # placeholder, normalized later
                        sort_order=max_sort + added + 1,
                    )
                    db.add(eq)
                    used_ids.add(r["id"])
                    added += 1
                    eq_rows.append(eq)

                if added > 0:
                    fix_log.append(f"自动补充了{added}道{type_names.get(qtype, qtype)}")
                elif added < shortfall:
                    fix_log.append(f"警告：{type_names.get(qtype, qtype)}题库不足，缺少{shortfall - added}道")

            # Re-normalize scores after count changes
            if fix_log:
                # Re-fetch eq_rows since we modified
                eq_rows = (await db.execute(
                    select(ExamQuestion).where(ExamQuestion.exam_id == exam_id).order_by(ExamQuestion.sort_order)
                )).scalars().all()
                if eq_rows:
                    base = expected_total // len(eq_rows)
                    remainder = expected_total - base * len(eq_rows)
                    for i, eq in enumerate(eq_rows):
                        eq.score = base + (1 if i < remainder else 0)

        await db.commit()

        # Re-check after fix
        eq_rows = (await db.execute(
            select(ExamQuestion).where(ExamQuestion.exam_id == exam_id).order_by(ExamQuestion.sort_order)
        )).scalars().all()
        actual_total_score = sum(eq.score for eq in eq_rows)
        actual_type_counts = {}
        for eq in eq_rows:
            q = (await db.execute(select(Question).where(Question.id == eq.question_id))).scalar_one_or_none()
            if q:
                actual_type_counts[q.type] = actual_type_counts.get(q.type, 0) + 1

        score_match = actual_total_score == expected_total
        count_match = len(eq_rows) == expected_count
        type_ok = all(
            actual_type_counts.get(qtype, 0) == expected_n
            for qtype, expected_n in expected_dist.items()
            if expected_n > 0
        )
        all_passed = score_match and count_match and type_ok

    # Build checks
    checks = [
        {
            "item": "总分校验",
            "passed": score_match,
            "detail": f"总分一致：{actual_total_score}分" if score_match else f"实际{actual_total_score}分，要求{expected_total}分",
            "expected": expected_total,
            "actual": actual_total_score,
        },
        {
            "item": "题量校验",
            "passed": count_match,
            "detail": f"题量一致：{len(eq_rows)}题" if count_match else f"实际{len(eq_rows)}题，要求{expected_count}题",
            "expected": expected_count if expected_count else len(eq_rows),
            "actual": len(eq_rows),
        },
        {
            "item": "题型分布校验",
            "passed": type_ok,
            "detail": "; ".join(type_details) if type_details else "所有题型数量符合要求",
            "expected": expected_dist,
            "actual": actual_type_counts,
        },
    ]

    suggestions = fix_log if fix_log else []

    return {
        "passed": all_passed,
        "checks": checks,
        "suggestions": suggestions,
        "auto_fixed": len(fix_log) > 0,
        "fix_log": fix_log,
    }


@router.get("/{exam_id}/answer-sheet")
async def export_answer_sheet(exam_id: int, db: AsyncSession = Depends(get_db)):
    """Export answer sheet (答题卡) as PDF only — matches exam question numbers."""
    exam_row = (await db.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if not exam_row:
        raise HTTPException(status_code=404, detail="Exam not found")

    eq_rows = (await db.execute(
        select(ExamQuestion).where(ExamQuestion.exam_id == exam_id).order_by(ExamQuestion.sort_order)
    )).scalars().all()

    questions = []
    for eq in eq_rows:
        q = (await db.execute(select(Question).where(Question.id == eq.question_id))).scalar_one_or_none()
        if q:
            questions.append({
                "type": q.type,
                "score": eq.score,
                "question": {
                    "content": q.content,
                    "options": q.options,
                    "answer": q.answer,
                    "explanation": q.explanation,
                },
            })

    exam_data = {
        "title": exam_row.title,
        "total_score": exam_row.total_score,
        "duration": exam_row.duration,
        "questions": questions,
    }

    content = generate_answer_sheet_pdf(exam_data).getvalue()
    filename = f"{exam_row.title}_答题卡.pdf".replace(" ", "_")
    ascii_fallback = f"answer_sheet_{exam_id}.pdf"
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_fallback}"; '
                f"filename*=UTF-8''{quote(filename)}"
            )
        },
    )


@router.delete("/{exam_id}")
async def delete_exam(exam_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an exam."""
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    await db.delete(exam)
    await db.commit()
    return {"status": "ok"}
