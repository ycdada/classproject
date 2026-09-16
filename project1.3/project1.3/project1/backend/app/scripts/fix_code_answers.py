"""One-off migration: fix single-line code answers and strip markdown fences.

Usage: python -m app.scripts.fix_code_answers  (run from backend/)
"""
import asyncio
import re
import sqlite3

DB_PATH = "./data/ds_teaching.db"

FENCE_RE = re.compile(r"^```[a-zA-Z]*\n?|\n?```$")

REFORMAT_SYSTEM = """你是代码排版工具。用户给你一段被压缩成一行的代码，请恢复成带换行和缩进的规范格式。

规则:
1. 只允许增删空白字符（换行、缩进），绝对不能修改任何代码逻辑、标识符、注释内容
2. 直接输出代码本身，不要用 markdown 代码块标记，不要任何解释"""


def strip_fences(text: str) -> str:
    return FENCE_RE.sub("", text.strip()).strip()


async def main():
    from app.services.llm_adapter import LLMAdapter

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("select id, answer from questions where type='code'")
    rows = cur.fetchall()

    llm = LLMAdapter()
    for qid, answer in rows:
        original = answer
        answer = strip_fences(answer)
        newlines = answer.count("\n")
        if newlines == 0 and len(answer) > 60:
            print(f"[q{qid}] single-line code ({len(answer)} chars) -> LLM reformat...")
            answer = strip_fences(await llm.chat(REFORMAT_SYSTEM, answer, temperature=0.0))
        if answer != original:
            cur.execute("update questions set answer=? where id=?", (answer, qid))
            print(f"[q{qid}] updated (newlines: {original.count(chr(10))} -> {answer.count(chr(10))})")
        else:
            print(f"[q{qid}] ok, skip")
    con.commit()
    con.close()


if __name__ == "__main__":
    asyncio.run(main())
