# 只保留一条 LangGraph 教学助手缝

现系统并行存在 `/api/chat`（function calling）与 `/api/v2/chat`（LangGraph + checkpoint + interrupt），前端只接了前者。决定删除旧对话通路，教师端唯一对话入口走 LangGraph：搜题、组卷、查知识、组卷后审核、题目草稿待审都经同一条图。对外路径仍是 `POST /api/chat`，避免前端再选择版本。
