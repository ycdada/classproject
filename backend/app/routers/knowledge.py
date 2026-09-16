from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ..database import get_db
from ..models.material import Material
from ..models.knowledge import KnowledgeNode
from ..schemas.knowledge import KnowledgeNodeOut, KnowledgeNodeUpdate
from ..services.llm_adapter import LLMAdapter

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
_llm = None


def _get_llm() -> LLMAdapter:
    global _llm
    if _llm is None:
        _llm = LLMAdapter()
    return _llm


def build_tree(nodes: list[KnowledgeNode], parent_id: int | None = None) -> list[dict]:
    """Build nested tree structure from flat node list."""
    result = []
    children = [n for n in nodes if n.parent_id == parent_id]
    children.sort(key=lambda n: n.sort_order)
    for node in children:
        d = KnowledgeNodeOut.model_validate(node).model_dump()
        d["children"] = build_tree(nodes, node.id)
        result.append(d)
    return result


@router.post("/extract/{material_id}")
async def extract_knowledge_tree(material_id: int, db: AsyncSession = Depends(get_db)):
    """Trigger LLM knowledge tree extraction for a material."""
    material = await db.get(Material, material_id)
    if not material or not material.content_md:
        raise HTTPException(404, "Material not found or not parsed")

    # Delete old tree
    await db.execute(
        delete(KnowledgeNode).where(KnowledgeNode.material_id == material_id)
    )

    # Extract from LLM
    try:
        tree_data = await _get_llm().extract_knowledge_tree(material.content_md)
    except Exception as e:
        raise HTTPException(500, f"LLM extraction failed: {str(e)}")

    # Save to DB
    nodes_created = 0
    for ch_idx, chapter in enumerate(tree_data.get("chapters", [])):
        ch_node = KnowledgeNode(
            material_id=material_id,
            parent_id=None,
            sort_order=ch_idx,
            name=chapter["name"],
            node_type="chapter",
        )
        db.add(ch_node)
        await db.flush()
        nodes_created += 1

        for sec_idx, section in enumerate(chapter.get("sections", [])):
            sec_node = KnowledgeNode(
                material_id=material_id,
                parent_id=ch_node.id,
                sort_order=sec_idx,
                name=section["name"],
                node_type="section",
            )
            db.add(sec_node)
            await db.flush()
            nodes_created += 1

            for pt_idx, point in enumerate(section.get("points", [])):
                pt_node = KnowledgeNode(
                    material_id=material_id,
                    parent_id=sec_node.id,
                    sort_order=pt_idx,
                    name=point["name"],
                    node_type="point",
                    definition=point.get("definition"),
                    key_terms=point.get("key_terms", []),
                    teaching_emphasis=point.get("teaching_emphasis"),
                    solution_steps=point.get("solution_steps") or "",
                    source_text=point.get("definition"),
                )
                db.add(pt_node)
                nodes_created += 1

    await db.commit()
    return {"status": "ok", "nodes_created": nodes_created}


@router.get("/tree/{material_id}")
async def get_knowledge_tree(material_id: int, db: AsyncSession = Depends(get_db)):
    """Get the knowledge tree for a material."""
    result = await db.execute(
        select(KnowledgeNode)
        .where(KnowledgeNode.material_id == material_id)
        .order_by(KnowledgeNode.sort_order)
    )
    nodes = result.scalars().all()
    return build_tree(nodes)


@router.put("/nodes/{node_id}")
async def update_knowledge_node(
    node_id: int, data: KnowledgeNodeUpdate, db: AsyncSession = Depends(get_db)
):
    """Edit a knowledge node (teacher manual correction)."""
    node = await db.get(KnowledgeNode, node_id)
    if not node:
        raise HTTPException(404, "Node not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(node, field, value)
    await db.commit()
    return {"status": "ok"}


@router.delete("/tree/{material_id}")
async def delete_knowledge_tree(material_id: int, db: AsyncSession = Depends(get_db)):
    """Delete the knowledge tree for a material."""
    await db.execute(
        delete(KnowledgeNode).where(KnowledgeNode.material_id == material_id)
    )
    await db.commit()
    return {"status": "ok"}
