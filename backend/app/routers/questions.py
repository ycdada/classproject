import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.material import Material
from ..models.question import Question
from ..schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionOut,
    QuestionFilter,
    QuestionListOut,
)
from ..services.question_service import QuestionService
from ..services.llm_adapter import LLMAdapter

router = APIRouter(prefix="/questions", tags=["questions"])


def get_service(db: AsyncSession = Depends(get_db)) -> QuestionService:
    return QuestionService(db)


# ── RAG search (must be before /{question_id}) ──

@router.get("/search")
async def search_questions(
    q: str,
    type: str | None = None,
    difficulty: int | None = None,
    chapter: str | None = None,
    top_k: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """RAG semantic search over the question bank."""
    service = QuestionService(db)
    where = {}
    if type:
        where["type"] = type
    if difficulty:
        where["difficulty"] = difficulty
    if chapter:
        where["chapter"] = chapter
    results = await service.search_semantic(q, top_k=top_k, where=where if where else None)
    return {"results": results}


@router.post("/embed-all")
async def reindex_questions(db: AsyncSession = Depends(get_db)):
    """Rebuild the entire ChromaDB index from the SQLite question bank."""
    service = QuestionService(db)
    count = await service.embed_all()
    return {"message": f"Re-indexed {count} questions", "count": count}


# ── CRUD endpoints ──

@router.get("")
async def list_questions(
    type: str | None = None,
    difficulty: int | None = None,
    chapter: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
    service: QuestionService = Depends(get_service),
):
    questions, total = await service.list_questions(
        page=page, page_size=page_size,
        qtype=type, difficulty=difficulty,
        chapter=chapter, keyword=keyword,
    )
    return {"total": total, "items": questions, "page": page, "page_size": page_size}


@router.get("/{question_id}", response_model=QuestionOut)
async def get_question(
    question_id: int,
    service: QuestionService = Depends(get_service),
):
    question = await service.get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.post("", response_model=QuestionOut, status_code=201)
async def create_question(
    data: QuestionCreate,
    service: QuestionService = Depends(get_service),
):
    return await service.create_question(data.model_dump())


@router.put("/{question_id}", response_model=QuestionOut)
async def update_question(
    question_id: int,
    data: QuestionUpdate,
    service: QuestionService = Depends(get_service),
):
    question = await service.update_question(question_id, data.model_dump(exclude_unset=True))
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.delete("/{question_id}", status_code=204)
async def delete_question(
    question_id: int,
    service: QuestionService = Depends(get_service),
):
    deleted = await service.delete_question(question_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Question not found")


@router.post("/batch-import", status_code=201)
async def batch_import(
    file: UploadFile = File(...),
    service: QuestionService = Depends(get_service),
):
    content = await file.read()

    if file.filename and file.filename.endswith(".json"):
        data = json.loads(content)
        questions_data = [QuestionCreate(**item).model_dump() for item in data]
    elif file.filename and file.filename.endswith(".xlsx"):
        import openpyxl
        from io import BytesIO
        wb = openpyxl.load_workbook(BytesIO(content), read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            raise HTTPException(status_code=400, detail="Empty file")
        headers = [str(h) for h in rows[0]]
        questions_data = []
        for row in rows[1:]:
            item = dict(zip(headers, row))
            if "knowledge_points" in item and isinstance(item["knowledge_points"], str):
                item["knowledge_points"] = [kp.strip() for kp in item["knowledge_points"].split(",")]
            if "options" in item and isinstance(item["options"], str):
                item["options"] = [opt.strip() for opt in item["options"].split("|")]
            if "tags" in item and isinstance(item["tags"], str):
                item["tags"] = [t.strip() for t in item["tags"].split(",")]
            if "difficulty" in item:
                item["difficulty"] = int(item["difficulty"])
            questions_data.append(QuestionCreate(**item).model_dump())
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use .json or .xlsx")

    count = 0
    for qdata in questions_data:
        await service.create_question(qdata)
        count += 1
    return {"imported": count}


@router.post("/extract/{material_id}")
async def extract_questions(material_id: int, db: AsyncSession = Depends(get_db)):
    """Extract embedded questions from a material using LLM."""
    material = await db.get(Material, material_id)
    if not material or not material.content_md:
        raise HTTPException(status_code=404, detail="Material not found or not parsed")

    llm = LLMAdapter()
    try:
        questions = await llm.extract_questions_from_text(material.content_md)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM extraction failed: {str(e)}")

    service = QuestionService(db)
    count = 0
    for q in questions:
        qdata = {
            "type": q.get("type", "choice"),
            "difficulty": q.get("difficulty", 3),
            "content": q.get("content", ""),
            "options": q.get("options"),
            "answer": str(q.get("answer", "")),
            "explanation": q.get("explanation"),
            "source": "ppt_extracted",
            "material_id": material_id,
            "chapter": q.get("chapter"),
        }
        await service.create_question(qdata)
        count += 1

    return {"status": "ok", "questions_extracted": count}
