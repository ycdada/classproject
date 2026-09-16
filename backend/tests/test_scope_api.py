"""考查范围审核流测试：propose → 改名 → 加节点 → confirm → 再 PUT 得 409。"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.database import init_db
from app.main import app


@pytest.fixture
async def client():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


DEMAND = {
    "title": "单元测验",
    "duration": 60,
    "total_score": 100,
    "teaching_progress": "已讲完树",
    "exam_scope": "二叉树遍历",
    "focus_notes": "先序遍历",
    "material_ids": [],
    "question_distribution": {"choice": 2},
    "difficulty_distribution": {"3": 100},
}


@pytest.mark.asyncio
async def test_propose_edit_confirm_409_flow(client):
    r = await client.post("/api/scopes/propose", json=DEMAND)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "proposed"
    assert isinstance(data["tree"], list)
    scope_id = data["id"]

    flat = []

    def walk(nodes):
        for n in nodes:
            flat.append(n)
            walk(n["children"])

    walk(data["tree"])
    # 空库时树可以为空；教师手动加一个章 + 点再继续
    if not flat:
        r = await client.post(
            f"/api/scopes/{scope_id}/nodes",
            json={"name": "第5章 树和二叉树", "node_type": "chapter"},
        )
        assert r.status_code == 200, r.text
        chapter_id = r.json()["id"]
        r = await client.post(
            f"/api/scopes/{scope_id}/nodes",
            json={"name": "教师补充点", "node_type": "point", "parent_id": chapter_id},
        )
        assert r.status_code == 200, r.text
        r = await client.get(f"/api/scopes/{scope_id}")
        data = r.json()
        flat = []

        def walk2(nodes):
            for n in nodes:
                flat.append(n)
                walk2(n["children"])

        walk2(data["tree"])
        assert flat
    target = flat[0]
    r = await client.put(
        f"/api/scopes/{scope_id}/nodes/{target['id']}",
        json={"name": "改名后的节点"},
    )
    assert r.status_code == 200

    r = await client.post(f"/api/scopes/{scope_id}/confirm")
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    r = await client.put(
        f"/api/scopes/{scope_id}/nodes/{target['id']}",
        json={"name": "不应生效"},
    )
    assert r.status_code == 409
