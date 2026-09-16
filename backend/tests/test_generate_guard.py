"""generate 守卫测试：proposed scope → 400；confirmed → 200 且题库不因缺口增加。"""
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


async def _make_scope(client, status: str) -> int:
    r = await client.post("/api/scopes/propose", json=DEMAND)
    assert r.status_code == 200, r.text
    scope_id = r.json()["id"]
    if status == "confirmed":
        r = await client.post(f"/api/scopes/{scope_id}/confirm")
        assert r.status_code == 200
    return scope_id


@pytest.mark.asyncio
async def test_generate_requires_confirmed_scope(client):
    scope_id = await _make_scope(client, "proposed")
    r = await client.post("/api/exams/generate", json={**DEMAND, "scope_id": scope_id})
    assert r.status_code == 400
    assert r.json()["detail"] == "scope_not_confirmed"


@pytest.mark.asyncio
async def test_generate_requires_scope_id(client):
    r = await client.post("/api/exams/generate", json=DEMAND)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_generate_missing_scope_404(client):
    r = await client.post("/api/exams/generate", json={**DEMAND, "scope_id": 999999})
    assert r.status_code == 404
