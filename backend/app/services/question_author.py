"""QuestionAuthor — 提出题目草稿的内部缝。生产适配器调 DeepSeek；测试注入假实现。"""
import json

from .llm_adapter import LLMAdapter

AUTHOR_SYSTEM_PROMPT = """你是《数据结构》课程的出题助手。根据给定的知识点上下文，拟出候选题（题目草稿）。

输出 JSON 数组:
[{
  "type": "choice|fill|tf|short_answer|code",
  "difficulty": 1-5,
  "chapter": "所属章节名称",
  "knowledge_point_ids": [],
  "content": "题干",
  "options": {"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"},
  "answer": "正确答案",
  "explanation": "解析说明"
}]

规则:
1. 只输出 count 道指定题型的题目草稿
2. 题目必须基于给定的知识点上下文（定义、术语、解题步骤、教学重点），不得编造知识
3. 选择题 options 必须有4个选项；判断题答案只能是"对"或"错"
4. 这些是候选草稿，教师确认后才会进入题库"""


class DeepSeekAuthor:
    """生产实现：调用 DeepSeek 拟草稿。"""

    def __init__(self, llm: LLMAdapter | None = None):
        self.llm = llm or LLMAdapter()

    async def propose(self, spec: dict, context: str) -> list[dict]:
        count = spec.get("count", 1)
        qtype = spec.get("type", "choice")
        difficulty = spec.get("difficulty", 3)
        user_prompt = (
            f"知识点上下文:\n{context[:6000]}\n\n"
            f"请拟 {count} 道 {qtype} 类型的题目草稿，难度约 {difficulty}/5。"
        )
        try:
            result = await self.llm.chat(AUTHOR_SYSTEM_PROMPT, user_prompt, temperature=0.5)
            data = self.llm._parse_json(result)
            if isinstance(data, dict):
                data = [data]
            if not isinstance(data, list):
                return []
            return [d for d in data if d.get("type") == qtype][:count]
        except Exception as e:
            print(f"[DeepSeekAuthor] propose failed: {e}")
            return []


def draft_from_author_item(item: dict, spec: dict) -> dict:
    """把 author 返回的题目归一成草稿存储形状。"""
    return {
        "type": spec.get("type", item.get("type", "choice")),
        "difficulty": item.get("difficulty", spec.get("difficulty", 3)),
        "chapter": item.get("chapter", ""),
        "knowledge_point_ids": item.get("knowledge_point_ids", item.get("knowledge_points", [])),
        "content": item.get("content", ""),
        "options": item.get("options"),
        "answer": item.get("answer", ""),
        "explanation": item.get("explanation", ""),
    }


def parse_author_output(text: str) -> list[dict]:
    """测试/调试辅助：解析 author 输出 JSON。"""
    return json.loads(text)
