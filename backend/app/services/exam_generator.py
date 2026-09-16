"""Exam generation — RAG retrieval + LLM assembly + AI question generation."""
import json
import re
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.question import Question
from ..models.knowledge import KnowledgeNode
from ..services.rag import RAGPipeline
from ..services.llm_adapter import LLMAdapter

# strip markdown code fences the LLM sometimes wraps answers in
_FENCE_RE = re.compile(r"^```[a-zA-Z]*\n?|\n?```$")


def _clean_answer(text: str) -> str:
    return _FENCE_RE.sub("", str(text).strip()).strip()


AI_GEN_SYSTEM_PROMPT = """你是一位《数据结构》课程出题专家。请根据给定的知识点和上下文，生成高质量的题目。

输出 JSON 数组:
[{
  "type": "choice|fill|tf|short_answer|code",
  "difficulty": 1-5,
  "chapter": "所属章节名称",
  "knowledge_points": ["知识点1"],
  "content": "题干",
  "options": {"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"},
  "answer": "正确答案",
  "explanation": "解析说明"
}]

规则:
1. 严格按照指定的知识点范围出题，不得偏离
2. 严格按照要求的题型和数量生成
3. 题目必须基于给定的教学材料上下文，确保知识准确性
4. 难度分布合理，符合要求
5. 选择题的 options 字段必须有4个选项
6. 判断题答案只能是"对"或"错"
7. 编程题题干需包含明确的输入输出要求
8. 答案必须准确无误，解析要清晰易懂
9. 每道题考察不同的知识点，避免重复
10. 编程题答案必须是带换行和缩进的完整规范代码（JSON 字符串中用 \\n 表示换行），严禁压缩成一行，也不要使用```代码块标记"""


def _normalize_scores(questions: list[dict], total_score: int) -> list[dict]:
    """Ensure sum of question scores exactly equals total_score."""
    count = len(questions)
    if count == 0:
        return questions
    base = total_score // count
    remainder = total_score - base * count
    for i, q in enumerate(questions):
        q["score"] = base + (1 if i < remainder else 0)
    return questions


class ExamGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMAdapter()
        self.rag = RAGPipeline()

    async def generate(self, requirements: dict) -> dict:
        """
        Generate exam by RAG retrieval + LLM assembly + AI generation fallback.
        requirements: {title, knowledge_node_ids, question_distribution,
                       difficulty, total_score, duration, scope}
        Returns: {questions: [{question_id, score, ...}], summary: str}
        """
        dist = requirements.get("question_distribution", {})
        node_ids = requirements.get("knowledge_node_ids", [])
        target_difficulty = requirements.get("difficulty", 3)
        scope = requirements.get("scope", "")
        total_score = requirements.get("total_score", 100)

        # Build knowledge context from selected nodes
        knowledge_context = await self._build_context(node_ids)
        if not knowledge_context and scope:
            knowledge_context = scope

        # Collect all candidates via RAG
        all_candidates = []
        missing_types = {}  # Track what we need vs what we have
        for qtype, count in dist.items():
            if count == 0:
                continue
            candidates = await self._retrieve_candidates(
                qtype, knowledge_context, count * 5, target_difficulty
            )
            # Attach required count info
            for c in candidates:
                c["_required_count"] = count
                c["_qtype"] = qtype
            all_candidates.extend(candidates)

            if len(candidates) < count:
                missing_types[qtype] = count - len(candidates)

        # Use AI to generate missing questions
        if missing_types:
            ai_questions = await self._generate_questions_with_ai(
                missing_types, requirements, knowledge_context
            )
            if ai_questions:
                # Save generated questions to bank
                saved = await self._save_generated_questions(ai_questions, node_ids)
                # Convert to candidate format and add
                for sq in saved:
                    all_candidates.append({
                        "question_id": sq["id"],
                        "type": sq["type"],
                        "difficulty": sq["difficulty"],
                        "chapter": sq.get("chapter", ""),
                        "content": sq["content"],
                        "options": sq.get("options"),
                        "answer": sq["answer"],
                        "explanation": sq.get("explanation", ""),
                        "knowledge_points": sq.get("knowledge_point_ids", []),
                        "_distance": 0.1,
                        "_required_count": missing_types.get(sq["type"], 1),
                        "_qtype": sq["type"],
                    })

        if not all_candidates:
            return {"questions": [], "summary": "题库中没有匹配的题目，且无法生成新题目。请上传相关教学材料或扩大知识范围。"}

        # Let LLM select and order the best questions
        assembled = await self._assemble_with_llm(
            all_candidates, requirements, knowledge_context
        )

        questions = assembled.get("questions", [])
        if questions:
            # Auto-fill gaps: ensure question counts match requested distribution
            questions = await self._auto_fill_gaps(
                questions, all_candidates, dist, knowledge_context
            )
            # Normalize scores to match total_score exactly
            questions = _normalize_scores(questions, total_score)
            assembled["questions"] = questions

        return assembled

    async def _auto_fill_gaps(self, questions: list[dict], candidates: list[dict],
                              dist: dict, knowledge_context: str) -> list[dict]:
        """After LLM assembly, fill any missing questions to match requested distribution."""
        # Count current questions by type
        current_counts = {}
        for q in questions:
            qid = q.get("question_id")
            # Look up type from candidates
            qtype = None
            for c in candidates:
                if c.get("question_id") == qid:
                    qtype = c.get("type") or c.get("_qtype")
                    break
            if qtype:
                current_counts[qtype] = current_counts.get(qtype, 0) + 1
                q["_type"] = qtype  # tag for later use

        # Build a candidate pool by type (deduplicated)
        candidate_pool = {}
        used_ids = {q.get("question_id") for q in questions}
        for c in candidates:
            qtype = c.get("type") or c.get("_qtype", "")
            if c["question_id"] in used_ids:
                continue
            candidate_pool.setdefault(qtype, []).append(c)

        # For each type with shortfall, add more from candidate pool
        for qtype, expected in dist.items():
            if expected == 0:
                continue
            current = current_counts.get(qtype, 0)
            shortfall = expected - current
            if shortfall <= 0:
                continue

            pool = candidate_pool.get(qtype, [])
            # If pool is insufficient, try RAG to get more
            if len(pool) < shortfall:
                more = await self._retrieve_candidates(
                    qtype, knowledge_context, shortfall * 3, 3
                )
                for c in more:
                    if c["question_id"] not in used_ids:
                        pool.append(c)
                        used_ids.add(c["question_id"])

            # Add the best available candidates
            added = 0
            for c in sorted(pool, key=lambda x: x.get("_distance", 1.0)):
                if added >= shortfall:
                    break
                questions.append({
                    "question_id": c["question_id"],
                    "score": 1,  # placeholder, will be normalized
                    "sort_order": len(questions),
                    "_type": qtype,
                })
                used_ids.add(c["question_id"])
                added += 1

        # Trim excess questions: for any type exceeding requested count, remove extras
        result = []
        type_counts = {}
        for q in questions:
            qtype = q.get("_type") or q.get("type", "")
            # Try to get type from candidate lookup
            if not qtype:
                qid = q.get("question_id")
                for c in candidates:
                    if c.get("question_id") == qid:
                        qtype = c.get("type") or c.get("_qtype", "")
                        break
            expected = dist.get(qtype, 0)
            current = type_counts.get(qtype, 0)
            if expected > 0 and current >= expected:
                continue  # skip this question (excess)
            type_counts[qtype] = current + 1
            result.append(q)

        # Re-index sort_order
        for i, q in enumerate(result):
            q["sort_order"] = i

        return result

    async def _retrieve_candidates(self, qtype: str, context: str,
                                    top_k: int, difficulty: int) -> list[dict]:
        """RAG retrieval for a specific question type."""
        if not context:
            return []
        query_embedding = await self.llm.embed(context[:500])
        where = {"type": qtype}
        results = self.rag.search(query_embedding, top_k=top_k, where=where)

        # Load full question data from DB
        ids = [r["id"] for r in results]
        if not ids:
            return []

        rows = (await self.db.execute(
            select(Question).where(Question.id.in_(ids))
        )).scalars().all()
        row_map = {r.id: r for r in rows}

        candidates = []
        for r in results:
            q = row_map.get(r["id"])
            if q:
                candidates.append({
                    "question_id": q.id,
                    "type": q.type,
                    "difficulty": q.difficulty,
                    "chapter": q.chapter,
                    "content": q.content,
                    "options": q.options,
                    "answer": q.answer,
                    "explanation": q.explanation,
                    "knowledge_points": q.knowledge_point_ids,
                    "_distance": r["distance"],
                })
        return candidates

    async def _generate_questions_with_ai(self, missing_types: dict,
                                           requirements: dict,
                                           knowledge_context: str) -> list[dict]:
        """Use AI to generate questions when RAG doesn't have enough."""
        target_difficulty = requirements.get("difficulty", 3)
        total_needed = sum(missing_types.values())

        type_descriptions = {
            "choice": "选择题",
            "fill": "填空题",
            "tf": "判断题",
            "short_answer": "简答题",
            "code": "编程题",
        }

        type_requirements = []
        for qtype, count in missing_types.items():
            type_requirements.append(f"- {type_descriptions.get(qtype, qtype)}: {count}道")

        user_prompt = f"""请根据以下教学材料上下文，生成 {total_needed} 道题目。

题型要求:
{chr(10).join(type_requirements)}
难度: {target_difficulty}/5

教学材料上下文（出题依据）:
{knowledge_context[:6000]}

请严格按照上述题型和数量要求生成题目，确保每题考察不同的知识点，答案准确无误。"""

        try:
            result = await self.llm.chat(AI_GEN_SYSTEM_PROMPT, user_prompt, temperature=0.5)
            questions = self.llm._parse_json(result)
            if isinstance(questions, dict):
                questions = [questions]
            if not isinstance(questions, list):
                return []
            # Filter only needed types
            filtered = [q for q in questions if q.get("type") in missing_types]
            return filtered
        except Exception as e:
            print(f"[ExamGenerator] AI question generation failed: {e}")
            return []

    async def _save_generated_questions(self, questions: list[dict],
                                         node_ids: list[int]) -> list[dict]:
        """Save AI-generated questions to question bank and ChromaDB."""
        from ..services.question_service import QuestionService
        qs = QuestionService(self.db)
        saved = []
        for q_data in questions:
            try:
                question = await qs.create_question({
                    "type": q_data.get("type", "choice"),
                    "difficulty": q_data.get("difficulty", 3),
                    "chapter": q_data.get("chapter", ""),
                    "knowledge_point_ids": q_data.get("knowledge_points", []),
                    "content": q_data.get("content", ""),
                    "options": q_data.get("options"),
                    "answer": _clean_answer(q_data.get("answer", "")),
                    "explanation": q_data.get("explanation", ""),
                    "source": "ai_generated",
                })
                saved.append({
                    "id": question.id,
                    "type": question.type,
                    "difficulty": question.difficulty,
                    "chapter": question.chapter,
                    "content": question.content,
                    "options": question.options,
                    "answer": question.answer,
                    "explanation": question.explanation,
                    "knowledge_point_ids": question.knowledge_point_ids,
                })
            except Exception as e:
                print(f"[ExamGenerator] Failed to save question: {e}")
        return saved

    async def _assemble_with_llm(self, candidates: list[dict],
                                  requirements: dict, context: str) -> dict:
        """Let LLM select and order the best questions from candidates."""
        dist = requirements.get("question_distribution", {})
        total = requirements.get("total_score", 100)

        candidates_json = json.dumps(candidates, ensure_ascii=False, default=str)
        system_prompt = f"""你是出卷专家。从候选题目中选择最适合的组成试卷。

教学材料上下文:
{context[:2000]}

规则:
1. 只能从候选题目中**选择**，不得编造或修改题目
2. 严格遵循题型分布: {json.dumps(dist, ensure_ascii=False)}
3. 总分: {total}分
4. 优先选择与知识点上下文更匹配的题目（_distance越小越相关）
5. 同一知识点不重复出题"""

        user_prompt = f"""候选题目:
{candidates_json[:8000]}

请选出合适的题目组成试卷。输出 JSON:
{{
  "questions": [
    {{"question_id": 1, "score": 5, "sort_order": 1}}
  ],
  "summary": "试卷说明（一句话）"
}}"""

        result = await self.llm.chat(system_prompt, user_prompt)
        return self.llm._parse_json(result)

    async def _build_context(self, node_ids: list[int]) -> str:
        """Build knowledge context from selected tree nodes."""
        if not node_ids:
            return ""
        result = await self.db.execute(
            select(KnowledgeNode).where(KnowledgeNode.id.in_(node_ids))
        )
        nodes = result.scalars().all()
        parts = []
        for n in nodes:
            parts.append(f"## {n.name}")
            if n.definition:
                parts.append(f"定义: {n.definition}")
            if n.key_terms:
                parts.append(f"术语: {', '.join(n.key_terms)}")
            if n.teaching_emphasis:
                parts.append(f"重点: {n.teaching_emphasis}")
        return "\n\n".join(parts)
