# 数据结构智能出卷系统

面向教师的数据结构课程备课与组卷工具。系统支持课程材料管理、知识树提取、题库维护、考查范围确认、组卷、题目草稿审核，以及试卷预览和导出。

## 主要流程

1. 上传课程讲义、课件或大纲，整理为课程材料。
2. 从材料中提取知识树，包含知识点定义、教学重点和解题步骤。
3. 填写出卷需求，生成考查范围并由教师确认。
4. 系统从现有题库装配试卷；题库不足时生成待审核的题目草稿。
5. 教师审核草稿、调整试卷并导出。

题目草稿经教师确认后才进入题库。组卷不会静默地把模型生成内容写入题库。

## 技术组成

- 前端：React 18、TypeScript、Vite、Ant Design、Zustand
- 后端：Python 3.11、FastAPI、SQLAlchemy、LangGraph
- 数据：SQLite、ChromaDB
- AI：DeepSeek 对话接口；本地中文向量模型用于语义检索

## 项目结构

```text
backend/       FastAPI 服务、业务模块、数据库模型和测试
frontend/      React 教师端
数据结构资料/  课程讲义和课件
scripts/       项目维护脚本
```

## 本地启动

首次运行前安装 Python 3.11 和 Node.js LTS。前后端需要分别在两个终端运行。

### 后端

在 PowerShell 中执行：

```powershell
cd D:\pjt\classproject\backend
py -3.11 -m venv .venv
New-Item -ItemType Directory -Force data, uploads
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

编辑 `backend\.env`，填入可用的 `DEEPSEEK_API_KEY`。需要 AI 功能时必须配置；不要将密钥提交到版本库。

启动服务：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

健康检查地址：<http://localhost:8000/api/health>

### 前端

在另一个 PowerShell 窗口执行：

```powershell
cd D:\pjt\classproject\frontend
npm install
npm run dev
```

浏览器打开 <http://localhost:5173>。Vite 会将 `/api` 请求代理到后端 `http://localhost:8000`。

如果 PowerShell 阻止激活脚本，无需激活虚拟环境；直接使用上面的 `.venv\Scripts\python.exe` 命令即可。

## 测试与构建

```powershell
cd D:\pjt\classproject\backend
.\.venv\Scripts\python.exe -m pytest -v
```

```powershell
cd D:\pjt\classproject\frontend
npm run build
```

## 本地数据

- SQLite 数据库：`backend\data\ds_teaching.db`
- ChromaDB 向量数据：`backend\data\chroma\`
- 上传文件：`backend\uploads\`
- LangGraph 检查点：`backend\checkpoints.db`

删除或替换这些文件会影响本机数据；需要重置时请先备份。
