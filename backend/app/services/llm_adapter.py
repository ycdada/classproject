"""DeepSeek API adapter — chat, function calling + local embeddings."""
import json
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

from ..config import settings

# Module-level singleton — SentenceTransformer load takes seconds; LLMAdapter is
# instantiated per-request in several services, so the model must be shared.
_EMBEDDING_MODEL = None


def _get_embedding_model() -> SentenceTransformer:
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        # Use local_files_only to avoid network; model cached after first download
        try:
            _EMBEDDING_MODEL = SentenceTransformer(
                settings.local_embedding_model, local_files_only=True
            )
        except Exception:
            _EMBEDDING_MODEL = SentenceTransformer(settings.local_embedding_model)
    return _EMBEDDING_MODEL


class LLMAdapter:
    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        self._model = settings.deepseek_model
        # Local embedding model (DeepSeek has no embedding API) — shared singleton
        self._embedding_model = _get_embedding_model()

    async def chat(self, system_prompt: str, user_prompt: str,
                   temperature: float = 0.3) -> str:
        """Simple chat — returns full response text."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content

    async def chat_stream(self, system_prompt: str, messages: list[dict],
                          temperature: float = 0.3):
        """Streaming chat — yields delta text chunks."""
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=full_messages,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    def _embed_sync(self, text: str) -> list[float]:
        """Generate embedding vector using local model (synchronous, runs in thread)."""
        return self._embedding_model.encode(text, normalize_embeddings=True).tolist()

    def _embed_batch_sync(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts using local model."""
        embeddings = self._embedding_model.encode(texts, normalize_embeddings=True)
        return [e.tolist() for e in embeddings]

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for a single text."""
        import asyncio
        return await asyncio.to_thread(self._embed_sync, text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        import asyncio
        return await asyncio.to_thread(self._embed_batch_sync, texts)

    async def chat_with_tools(self, system_prompt: str, messages: list[dict],
                              tools: list[dict]) -> dict:
        """Chat with function calling — returns the tool call or text response.
        Returns: {type: "tool_call", name: str, arguments: dict}
              or: {type: "text", content: str}
        """
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=full_messages,
            tools=tools,
            temperature=0.3,
        )
        msg = response.choices[0].message
        if msg.tool_calls:
            tc = msg.tool_calls[0]
            return {
                "type": "tool_call",
                "name": tc.function.name,
                "arguments": json.loads(tc.function.arguments),
            }
        return {"type": "text", "content": msg.content or ""}

    async def extract_knowledge_tree(self, markdown_content: str) -> dict:
        """Extract knowledge tree structure from teaching material."""
        system_prompt = """你是课程教学专家。请从以下教学材料中提取知识点树结构。

输出 JSON 格式:
{
  "chapters": [
    {
      "name": "章节名称",
      "sections": [
        {
          "name": "小节名称",
          "points": [
            {
              "name": "知识点名称",
              "definition": "概念定义原文或紧贴原文的转述",
              "key_terms": ["术语1", "术语2"],
              "solution_steps": "材料中的解题或算法步骤；没有则空字符串",
              "teaching_emphasis": "教学重点说明"
            }
          ]
        }
      ]
    }
  ]

规则:
1. 从材料中提取真实的知识结构，层级为 章→节→知识点
2. 每个章节必须有 sections, 每个 section 必须有 points
3. definition 和 teaching_emphasis 从材料中总结
4. key_terms 提取关键术语
5. solution_steps 只能写材料中讲授的解题或算法步骤原文，不得编造；材料没有就给空字符串
6. 只提取材料中实际包含的内容，不编造"""

        result = await self.chat(system_prompt, f"请提取以下材料的知识树:\n\n{markdown_content[:12000]}")
        return self._parse_json(result)

    async def extract_questions_from_text(self, markdown_content: str) -> list[dict]:
        """Extract fixed questions from teaching material text. Never generates new ones."""
        system_prompt = """你是题库整理专家。请从以下教学材料中**提取**所有已有题目。

输出 JSON 数组:
[{
  "type": "choice|fill|tf|short_answer|code",
  "difficulty": 1-5,
  "chapter": "所属章节名称",
  "knowledge_points": ["知识点1", "知识点2"],
  "content": "题干原文",
  "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "answer": "正确答案",
  "explanation": "解析（如有）"
}]

规则:
1. 只提取材料中**已有**的题目，绝不编造
2. 选择题的 options 字段必填，其他题型可省略
3. difficulty 根据题目复杂度估算（1最简单，5最难）
4. chapter 推断所属章节"""

        result = await self.chat(system_prompt, f"请提取以下材料中的所有题目:\n\n{markdown_content[:12000]}")
        return self._parse_json(result)

    def _parse_json(self, text: str) -> dict | list:
        """Extract JSON from LLM response text."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        return json.loads(text)
