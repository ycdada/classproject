"""ScopeBuilder — 根据出卷需求从课程知识树筛选组织出考查范围（proposed）。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.knowledge import KnowledgeNode
from ..models.material import Material
from ..models.scope import ExamScope, ExamScopeNode


class ScopeBuilder:
    """提出一份可审核的考查范围树。无 LLM 时用子串匹配过滤。"""

    def __init__(self, db: AsyncSession, llm=None):
        self.db = db
        self.llm = llm

    async def propose(self, demand: dict) -> ExamScope:
        material_ids = demand.get("material_ids") or []
        if material_ids:
            rows = await self.db.execute(
                select(KnowledgeNode).where(KnowledgeNode.material_id.in_(material_ids))
            )
        else:
            rows = await self.db.execute(select(KnowledgeNode))
        nodes = rows.scalars().all()

        kept = self._filter_nodes(nodes, demand)

        scope = ExamScope(status="proposed", demand_json=demand)
        self.db.add(scope)
        await self.db.flush()

        id_map: dict[int, int] = {}
        for node in kept:  # parents precede children (see _filter_nodes)
            sn = ExamScopeNode(
                scope_id=scope.id,
                parent_id=id_map.get(node.parent_id),
                source_node_id=node.id,
                sort_order=node.sort_order,
                name=node.name,
                node_type=node.node_type,
                definition=node.definition,
                key_terms=node.key_terms,
                teaching_emphasis=node.teaching_emphasis,
                solution_steps=node.solution_steps,
                included=True,
            )
            self.db.add(sn)
            await self.db.flush()
            id_map[node.id] = sn.id

        await self.db.commit()
        await self.db.refresh(scope)
        return scope

    def _filter_nodes(self, nodes: list[KnowledgeNode], demand: dict) -> list[KnowledgeNode]:
        """保留命中的点及其祖先链；章/节仅当有后代被保留才保留。返回保持父先于子的列表。"""
        by_id = {n.id: n for n in nodes}
        children_of: dict[int | None, list[KnowledgeNode]] = {}
        for n in nodes:
            children_of.setdefault(n.parent_id, []).append(n)
        for lst in children_of.values():
            lst.sort(key=lambda n: n.sort_order)

        if self.llm is not None:
            matched = self._llm_filter(nodes, demand)
        else:
            matched = self._substring_filter(nodes, demand)

        keep_ids: set[int] = set()
        for node in matched:
            cur: KnowledgeNode | None = node
            while cur is not None:
                keep_ids.add(cur.id)
                cur = by_id.get(cur.parent_id)

        # 祖先链上的章/节只有当确有命中点挂在其下时才保留
        def walk_up(cur_id: int | None) -> bool:
            while cur_id is not None:
                parent = by_id.get(cur_id)
                if parent is None:
                    return False
                if parent.id == node.id:
                    return True
                cur_id = parent.parent_id
            return False

        kept = []
        for node in nodes:
            if node.id not in keep_ids:
                continue
            if node.node_type == "point":
                kept.append(node)
            elif any(walk_up(m.parent_id) for m in matched):
                kept.append(node)

        kept.sort(key=lambda n: self._depth_key(by_id, n))
        return kept

    def _substring_filter(self, nodes: list[KnowledgeNode], demand: dict) -> list[KnowledgeNode]:
        texts = [
            str(demand.get("teaching_progress") or ""),
            str(demand.get("exam_scope") or ""),
            str(demand.get("focus_notes") or ""),
        ]
        # 先按常见分隔符切开，再把连续中文按 2 字滑窗切成短词，逐词匹配
        import re
        words: list[str] = []
        for t in texts:
            for seg in re.split(r"[，。、；：,!;:\s]+", t):
                seg = seg.strip()
                if not seg:
                    continue
                if len(seg) <= 4:
                    words.append(seg)
                else:
                    for i in range(len(seg) - 1):
                        words.append(seg[i:i + 2])
        keywords = [w for w in dict.fromkeys(words) if w]
        matched = []
        for n in nodes:
            if n.node_type != "point":
                continue
            hay = " ".join(filter(None, [n.name, n.definition or "", n.teaching_emphasis or ""]))
            if any(k in hay for k in keywords):
                matched.append(n)
        return matched

    def _llm_filter(self, nodes: list[KnowledgeNode], demand: dict) -> list[KnowledgeNode]:
        # LLM 辅助过滤是增强路径；实现时按子串匹配同样的输出契约调用。
        return self._substring_filter(nodes, demand)

    @staticmethod
    def _depth_key(by_id: dict[int, KnowledgeNode], node: KnowledgeNode):
        depth = 0
        cur = node
        while cur.parent_id is not None:
            depth += 1
            cur = by_id[cur.parent_id]
        return (depth, node.sort_order, node.id)
