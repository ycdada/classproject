"""考查范围 HTTP：提出、查看、修改节点、增删节点、确认。确认后节点只读。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.scope import ExamScope, ExamScopeNode
from ..schemas.exam import ExamRequirements
from ..schemas.scope import (
    ExamScopeNodeCreate,
    ExamScopeNodeOut,
    ExamScopeNodeUpdate,
)
from ..services.scope_builder import ScopeBuilder

router = APIRouter(prefix="/scopes", tags=["scopes"])


def build_scope_tree(nodes: list[ExamScopeNode], parent_id: int | None = None) -> list[dict]:
    result = []
    children = sorted(
        (n for n in nodes if n.parent_id == parent_id), key=lambda n: n.sort_order
    )
    for node in children:
        d = ExamScopeNodeOut.model_validate(node).model_dump()
        d["children"] = build_scope_tree(nodes, node.id)
        result.append(d)
    return result


async def _get_scope_or_404(db: AsyncSession, scope_id: int) -> ExamScope:
    scope = await db.get(ExamScope, scope_id)
    if not scope:
        raise HTTPException(404, "Scope not found")
    return scope


@router.post("/propose")
async def propose_scope(demand: ExamRequirements, db: AsyncSession = Depends(get_db)):
    """根据出卷需求提出一份考查范围（proposed）。"""
    scope = await ScopeBuilder(db).propose(demand.model_dump())
    return await _scope_payload(db, scope)


@router.get("/{scope_id}")
async def get_scope(scope_id: int, db: AsyncSession = Depends(get_db)):
    scope = await _get_scope_or_404(db, scope_id)
    return await _scope_payload(db, scope)


@router.put("/{scope_id}/nodes/{node_id}")
async def update_scope_node(
    scope_id: int, node_id: int, data: ExamScopeNodeUpdate,
    db: AsyncSession = Depends(get_db),
):
    scope = await _get_scope_or_404(db, scope_id)
    if scope.status == "confirmed":
        raise HTTPException(409, "scope already confirmed")
    node = await db.get(ExamScopeNode, node_id)
    if not node or node.scope_id != scope_id:
        raise HTTPException(404, "Scope node not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(node, field, value)
    await db.commit()
    return {"status": "ok"}


@router.post("/{scope_id}/nodes", response_model=ExamScopeNodeOut)
async def add_scope_node(
    scope_id: int, data: ExamScopeNodeCreate, db: AsyncSession = Depends(get_db)
):
    scope = await _get_scope_or_404(db, scope_id)
    if scope.status == "confirmed":
        raise HTTPException(409, "scope already confirmed")
    if data.parent_id is not None:
        parent = await db.get(ExamScopeNode, data.parent_id)
        if not parent or parent.scope_id != scope_id:
            raise HTTPException(404, "Parent node not found")
    siblings = (await db.execute(
        select(ExamScopeNode)
        .where(ExamScopeNode.scope_id == scope_id, ExamScopeNode.parent_id == data.parent_id)
    )).scalars().all()
    node = ExamScopeNode(
        scope_id=scope_id,
        parent_id=data.parent_id,
        source_node_id=None,
        sort_order=len(siblings),
        name=data.name,
        node_type=data.node_type,
        definition=data.definition,
        key_terms=data.key_terms,
        teaching_emphasis=data.teaching_emphasis,
        solution_steps=data.solution_steps,
        included=data.included,
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return node


@router.delete("/{scope_id}/nodes/{node_id}")
async def delete_scope_node(
    scope_id: int, node_id: int, db: AsyncSession = Depends(get_db)
):
    scope = await _get_scope_or_404(db, scope_id)
    if scope.status == "confirmed":
        raise HTTPException(409, "scope already confirmed")
    node = await db.get(ExamScopeNode, node_id)
    if not node or node.scope_id != scope_id:
        raise HTTPException(404, "Scope node not found")
    await _delete_subtree(db, node)
    await db.commit()
    return {"status": "ok"}


async def _delete_subtree(db: AsyncSession, node: ExamScopeNode):
    children = (await db.execute(
        select(ExamScopeNode).where(ExamScopeNode.parent_id == node.id)
    )).scalars().all()
    for child in children:
        await _delete_subtree(db, child)
    await db.delete(node)


@router.post("/{scope_id}/confirm")
async def confirm_scope(scope_id: int, db: AsyncSession = Depends(get_db)):
    scope = await _get_scope_or_404(db, scope_id)
    if scope.status == "confirmed":
        raise HTTPException(409, "scope already confirmed")
    scope.status = "confirmed"
    await db.commit()
    return await _scope_payload(db, scope)


async def _scope_payload(db: AsyncSession, scope: ExamScope) -> dict:
    nodes = (await db.execute(
        select(ExamScopeNode).where(ExamScopeNode.scope_id == scope.id)
    )).scalars().all()
    return {
        "id": scope.id,
        "status": scope.status,
        "demand": scope.demand_json,
        "tree": build_scope_tree(nodes),
    }
