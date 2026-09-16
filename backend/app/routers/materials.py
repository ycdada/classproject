import os
import shutil

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models.material import Material
from ..schemas.material import MaterialOut, MaterialListItem
from ..services.file_parser import FileParser

router = APIRouter(prefix="/materials", tags=["materials"])
parser = FileParser()
UPLOAD_DIR = "uploads"

ALLOWED_KINDS = {"lecture_notes", "slides", "syllabus", "other"}


@router.post("/upload", response_model=MaterialOut)
async def upload_material(
    file: UploadFile = File(...),
    kind: str = Form("other"),
    chapter: int | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload and parse a teaching material file."""
    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("pptx", "docx", "pdf", "md"):
        raise HTTPException(400, f"Unsupported file type: {ext}")

    if not kind:
        kind = "slides" if ext == "pptx" else "other"
    if kind not in ALLOWED_KINDS:
        raise HTTPException(400, f"Invalid kind: {kind}. Allowed: {sorted(ALLOWED_KINDS)}")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        content_md, page_count = parser.parse(file_path, ext)
    except Exception as e:
        raise HTTPException(500, f"Parse error: {str(e)}")

    material = Material(
        filename=file.filename,
        file_type=ext,
        file_path=file_path,
        kind=kind,
        chapter=chapter,
        content_md=content_md,
        page_count=page_count,
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)
    return material


@router.get("", response_model=list[MaterialListItem])
async def list_materials(db: AsyncSession = Depends(get_db)):
    """List all uploaded materials."""
    result = await db.execute(
        select(Material).order_by(Material.uploaded_at.desc())
    )
    return result.scalars().all()


@router.get("/{material_id}", response_model=MaterialOut)
async def get_material(material_id: int, db: AsyncSession = Depends(get_db)):
    """Get parsed material content."""
    material = await db.get(Material, material_id)
    if not material:
        raise HTTPException(404, "Material not found")
    return material


@router.delete("/{material_id}")
async def delete_material(material_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a material and its knowledge tree."""
    material = await db.get(Material, material_id)
    if not material:
        raise HTTPException(404, "Material not found")
    if os.path.exists(material.file_path):
        os.remove(material.file_path)
    await db.delete(material)
    await db.commit()
    return {"status": "ok"}
