"""ChatService — 旧版 function-calling 直答路径（v3 已由 agent_v2 单一 LangGraph 取代）。

TOOLS 定义保留给 router prompt 复用；generate 路径已下线——组卷必须先经
ScopeBuilder 提出考查范围并确认（见 app/services/paper_assembler.py）。
"""
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .llm_adapter import LLMAdapter
from .rag import RAGPipeline
from .question_service import QuestionService


CHAT_SYSTEM_PROMPT = """你是一位《数据结构》课程的教学助手，帮助老师出卷、查题、解答知识问题。

你的能力:
1. 搜题 — 根据关键词或知识点在题库中语义搜索题目
2. 组卷 — 根据老师需求组合试卷
3. 知识问答 — 回答数据结构相关概念问题

工具使用规则（必须遵守）:
- 老师提出组卷/出卷需求时，只要能推断出大致范围，就必须调用 generate_exam 工具，绝不能只用文字描述方案而不调用工具
- 老师对你之前给出的方案表示确认（如"可以""好的""生成吧""就这样"）时，必须立即调用 generate_exam
- 只有当考试范围完全无法推断时才向老师追问，且最多追问一次
- 找题用 search_questions，概念问题用 query_knowledge

重要:
- 题目必须来自题库，不可编造
- 组卷时严格遵循老师指定的范围"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_questions",
            "description": "在题库中语义搜索题目，返回匹配的题目列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词或知识点描述"},
                    "type": {"type": "string", "enum": ["choice", "fill", "tf", "short_answer", "code"]},
                    "difficulty": {"type": "integer", "minimum": 1, "maximum": 5},
                    "count": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_exam",
            "description": "根据自然语言描述生成试卷",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "试卷标题"},
                    "scope": {"type": "string", "description": "考试范围描述，如'第1-3章'或'树和图'"},
                    "choice_count": {"type": "integer", "default": 10},
                    "fill_count": {"type": "integer", "default": 5},
                    "tf_count": {"type": "integer", "default": 5},
                    "short_answer_count": {"type": "integer", "default": 3},
                    "code_count": {"type": "integer", "default": 2},
                    "difficulty": {"type": "integer", "minimum": 1, "maximum": 5},
                    "total_score": {"type": "integer", "default": 100},
                    "duration": {"type": "integer", "default": 120},
                },
                "required": ["title", "scope"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_knowledge",
            "description": "查询数据结构知识点定义和解释",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "要查询的知识点，如'二叉树的遍历'"},
                },
                "required": ["topic"],
            },
        },
    },
]


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMAdapter()
        self.rag = RAGPipeline()
        self.question_service = QuestionService(db)

    async def process_message(self, message: str, history: list[dict]):
        """Process a user message, return SSE events as dicts.

        组卷意图不再在此直接生成试卷——按 ADR-0006，组卷必须先确认考查范围，
        由 agent_v2 的 propose_scope → scope_review → assemble 流程处理。
        """
        messages = history + [{"role": "user", "content": message}]

        # Step 1: Determine intent with function calling
        tool_result = await self.llm.chat_with_tools(
            CHAT_SYSTEM_PROMPT, messages, TOOLS
        )

        if tool_result["type"] == "tool_call":
            # Step 2: Execute the tool
            tool_name = tool_result["name"]
            tool_args = tool_result["arguments"]

            if tool_name == "search_questions":
                result = await self._handle_search(tool_args)
            elif tool_name == "generate_exam":
                result = {
                    "guidance": "组卷需要先确认考查范围。请使用组卷向导，或让我先为您提出考查范围。",
                    "next_step": "propose_scope",
                }
            elif tool_name == "query_knowledge":
                result = await self._handle_query_knowledge(tool_args)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            # Step 3: Stream the result with LLM commentary
            yield {"event": "tool_call", "data": json.dumps({
                "name": tool_name, "arguments": tool_args, "result": result
            }, ensure_ascii=False)}

            # Let LLM summarize the results
            summary_prompt = f"用户请求已执行。工具 {tool_name} 返回了结果。请用自然语言向老师汇报结果。"
            full_messages = messages + [
                {"role": "assistant", "content": None, "tool_calls": [
                    {"id": "call_1", "type": "function",
                     "function": {"name": tool_name, "arguments": json.dumps(tool_args)}}
                ]},
                {"role": "tool", "tool_call_id": "call_1",
                 "content": json.dumps(result, ensure_ascii=False)},
                {"role": "user", "content": summary_prompt},
            ]
            async for chunk in self.llm.chat_stream(CHAT_SYSTEM_PROMPT, full_messages):
                yield {"event": "text", "data": chunk}
        else:
            # Direct text response — stream it
            async for chunk in self.llm.chat_stream(CHAT_SYSTEM_PROMPT, messages):
                yield {"event": "text", "data": chunk}

        yield {"event": "done", "data": ""}

    async def _handle_search(self, args: dict) -> dict:
        where = {}
        if args.get("type"):
            where["type"] = args["type"]
        if args.get("difficulty"):
            where["difficulty"] = args["difficulty"]
        results = await self.question_service.search_semantic(
            args["query"], top_k=args.get("count", 10), where=where if where else None
        )
        return {
            "query": args["query"],
            "count": len(results),
            "results": results[:args.get("count", 10)],
        }

    async def _handle_query_knowledge(self, args: dict) -> dict:
        from ..models.knowledge import KnowledgeNode
        topic = args["topic"]
        result = await self.db.execute(
            select(KnowledgeNode).where(KnowledgeNode.name.contains(topic))
        )
        nodes = result.scalars().all()
        return {
            "topic": topic,
            "results": [
                {"name": n.name, "definition": n.definition,
                 "key_terms": n.key_terms, "teaching_emphasis": n.teaching_emphasis}
                for n in nodes[:5]
            ],
        }
