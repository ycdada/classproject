# 压平目录并允许重建本地库

运行中的应用从 `project1.3/project1.3/project1/` 升到仓库根目录的 `backend/` 与 `frontend/`。本地 SQLite、Chroma、LangGraph checkpoints 允许清空重建；课件 PPT 保留并可重新导入。压平是为了去掉三层套娃路径，并使新旧树可以并排做差异度量（旧树冻结在 `baselines/`）。
