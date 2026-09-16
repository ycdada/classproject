# 项目协作说明

## 开始工作前

- 先阅读 `README.md` 了解启动方式，再阅读 `CONTEXT.md` 对齐业务术语。
- 修改前检查相关路由、服务、数据模型、Schema 和前端调用，沿用现有模块职责。
- 以仓库当前代码和可运行功能为准；不要引用仓库中不存在的文件或目录。

## 项目约定

- 前端使用 React、TypeScript、Vite、Ant Design 和 Zustand；后端使用 FastAPI、SQLAlchemy 与 LangGraph。
- 保持前后端 API 字段与响应结构一致。跨层修改时同步更新 Schema、服务、路由、类型定义及调用代码。
- 组卷必须使用已确认的考查范围。试卷从题库选择已有题目；缺少题目时创建待审核的题目草稿。
- 只有教师接受的题目草稿才能进入题库；未接受的草稿不能被加入试卷。
- 不要在没有明确要求时清空或替换 `backend/data/`、`backend/uploads/`、`backend/checkpoints.db` 中的数据。
- 配置密钥保存在本地 `.env`，不得写入源码、日志、测试输出或提交记录。

## 验证

按修改范围运行适当检查；涉及后端业务时运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

涉及前端时运行：

```powershell
cd frontend
npm run build
```

最终说明应列明实际运行的检查及结果；未运行的检查不要表述为已通过。
