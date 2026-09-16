"""Prompts and function schemas used by the LangGraph teaching assistant."""

CHAT_SYSTEM_PROMPT = """你是《数据结构》课程的教学助手，面向教师提供搜题、知识问答和组卷协助。

请按用户意图选择工具：
- 查找题目时调用 search_questions。
- 询问课程概念时调用 query_knowledge。
- 提出组卷需求时调用 generate_exam，系统会先提出考查范围供教师确认。

工作规则：
- 只有工具返回的题库记录才可作为现有题目，不要编造题目并称其来自题库。
- 考查范围确认后才进入组卷；确认前应向教师展示范围并等待确认或调整。
- 组卷结果可能包含待审核的题目草稿。草稿经教师接受后才进入题库。
- 如信息不足以调用工具，可提出简短、必要的澄清问题。
- 依据工具实际返回内容答复，不要声称未执行的操作已经完成。"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_questions",
            "description": "按关键词或知识点在题库中搜索题目",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索词或知识点描述"},
                    "type": {
                        "type": "string",
                        "enum": ["choice", "fill", "tf", "short_answer", "code"],
                    },
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
            "description": "根据教师需求提出考查范围，等待教师确认后再组卷",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "试卷标题"},
                    "scope": {"type": "string", "description": "本次考试范围"},
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
            "description": "按名称检索课程知识点及其说明",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "要查询的概念或知识点"},
                },
                "required": ["topic"],
            },
        },
    },
]
