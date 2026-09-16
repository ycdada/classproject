# 前端换 React，后端留 FastAPI

完善版必须换栈以拉开与现系统、与原文档的差异，但产品仍是纯教师端出卷。决定只换前端：Vue 3 + Naive UI 改为 React 18 + TypeScript + Vite + Ant Design 5 + React Router + Zustand；后端保持 FastAPI + SQLAlchemy + Chroma + DeepSeek + LangGraph。

换前端能使全部页面从 SFC 变成 TSX，原文档中的 Vue 技术叙事也必须重写。后端再换框架会把 LangGraph / SSE / 异步会话一起推翻，超出「功能集合不变」的范围，也难以一次交接完成。
