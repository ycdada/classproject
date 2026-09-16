"""agent_v2 测试入口 — 覆盖 Phase 1~3 验收用例。

用法（在 backend 目录下）：
    python -m agent_v2.main

注意：搜题 / 组卷 / 知识查询的意图路由与最终对话都依赖 DeepSeek API，
需要 .env 中配置有效的 DEEPSEEK_API_KEY 才能跑通。
"""
import json

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from .graph import app


def _show(tag: str, result: dict):
    """打印一次调用的关键结果。"""
    print(f"\n===== {tag} =====")
    if "__interrupt__" in result:
        iv = result["__interrupt__"][0].value
        print("[interrupt] 命中暂停，等待审核")
        print("  审核对象 keys:", list(iv.get("exam_paper", {}).keys()))
        print("  review_status:", result.get("review_status"))
        return
    last = result.get("messages", [])
    if last:
        print("[回复]", getattr(last[-1], "content", last[-1]))
    print("  review_status:", result.get("review_status"))
    if result.get("tool_result"):
        print("  tool_result keys:", list(result["tool_result"].keys()))


def test_search():
    result = app.invoke(
        {"messages": [HumanMessage(content="帮我找10道二叉树相关的选择题")]},
        config={"configurable": {"thread_id": "demo_search"}},
    )
    _show("测试1：语义搜题", result)


def test_knowledge():
    result = app.invoke(
        {"messages": [HumanMessage(content="第三章的知识点有哪些")]},
        config={"configurable": {"thread_id": "demo_knowledge"}},
    )
    _show("测试3：知识查询", result)


def test_generate_and_review():
    config = {"configurable": {"thread_id": "demo_generate"}}
    result = app.invoke(
        {"messages": [HumanMessage(content="帮我出一份数据结构期中考试卷，选择题10道，难度3")]},
        config=config,
    )
    _show("测试2：组卷（应暂停在审核节点）", result)

    if "__interrupt__" in result:
        print("\n>>> 模拟教师审核通过，恢复执行")
        result2 = app.invoke(Command(resume={"approved": True}), config=config)
        _show("测试2b：审核通过后", result2)


def test_resume_continuity():
    """验证 Checkpoint 断线续聊：同一 thread_id 第二轮能记住历史。"""
    config = {"configurable": {"thread_id": "demo_continuity"}}
    app.invoke(
        {"messages": [HumanMessage(content="帮我找几道栈和队列相关的题")]},
        config=config,
    )
    result2 = app.invoke(
        {"messages": [HumanMessage(content="刚才找到的题目里，难度是3的有几道")]},
        config=config,
    )
    _show("测试4：断线续聊（第二轮）", result2)


if __name__ == "__main__":
    try:
        test_search()
        test_knowledge()
        test_generate_and_review()
        test_resume_continuity()
        print("\n全部测试执行完毕。")
    except Exception as e:
        print(f"\n[失败] {type(e).__name__}: {e}")
        print("提示：请确认 .env 中已配置有效的 DEEPSEEK_API_KEY，且网络可访问 DeepSeek。")
