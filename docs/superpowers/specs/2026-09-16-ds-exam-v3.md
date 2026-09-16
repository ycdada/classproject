# 数据结构智能出卷完善版

Status: ready-for-agent

对照当前可运行系统与 `原文档/` 做一次完善：前端换栈、组卷主线严格符合基础需求、题库缺口走题目草稿、工程与学术文档全部按新术语重写，两套基线均达到可度量的 30% 差异。

## Problem Statement

教师需要根据自己的教案、PPT 和课程大纲出一套贴合本班进度的数据结构试卷。现系统能上传材料、抽出知识树、从表单组卷并导出，但有三处对不上基础需求：材料理解缺少解题步骤；出卷需求没有教学进度和考试范围字段，也不会先生成一份可审核的考查范围树；题库不够时模型写的题会直接进题库。同时完善版必须在源码和原文档上都能看出不是换皮。

## Solution

教师仍只使用教师端。上传教案 / PPT / 大纲进入课程材料库；系统抽出章—节—点，并带上术语、定义、解题步骤、教学重点。教师填写出卷需求后，系统生成考查范围树，教师改完确认，再组卷。试卷只含题库中的题目；缺口变成题目草稿，确认后才入库。前端用 React + Ant Design 重写全部页面，后端留 FastAPI + LangGraph。完成后用脚本对照两套基线验收 30%，并且看起来像新版。

## User Stories

1. As a 教师, I want to upload 教案、PPT and 课程大纲 into the 课程材料库, so that all course files live in one place.
2. As a 教师, I want each 材料 tagged as 教案 / PPT / 大纲 / 其他, so that I can tell them apart in the library.
3. As a 教师, I want unsupported files rejected with a clear error, so that I do not think a failed parse succeeded.
4. As a 教师, I want a 材料 list and detail with parsed text, so that I can check what the system read.
5. As a 教师, I want to delete a 材料 and its derived 知识树, so that obsolete files leave the library.
6. As a 教师, I want the system to extract 知识节点 from a 材料, so that I do not build the tree by hand.
7. As a 教师, I want each 知识点 to carry 专业术语、概念定义、解题步骤 and 教学重点 taken from the 材料, so that later papers follow how I actually teach.
8. As a 教师, I want the 知识树 shown as a tree I can expand, so that I can see chapter / section / point.
9. As a 教师, I want to edit a 知识节点 (name, definition, terms, steps, emphasis), so that extraction mistakes do not leak into exams.
10. As a 教师, I want to add or remove a 知识节点 on the course 知识树, so that the tree matches the course.
11. As a 教师, I want to enter 出卷需求 including 教学进度、考试范围、题型要求、难度要求 and 重点考查方向, so that the system knows this sitting of the exam.
12. As a 教师, I want to also set title, duration and total score as part of 出卷需求, so that the paper header is complete.
13. As a 教师, I want the system to filter, adjust and organize 知识节点 into a 考查范围 for this 出卷需求, so that I am not assembling the exam scope only by ticking ids.
14. As a 教师, I want the 考查范围 shown as a tree, so that I can see what will be tested.
15. As a 教师, I want to check, uncheck, rename, edit and add nodes on the 考查范围, so that the scope matches my intent.
16. As a 教师, I want to confirm the 考查范围, so that 组卷 cannot start on an unreviewed tree.
17. As a 教师, I want 组卷 blocked until 考查范围 is confirmed, so that papers cannot skip the review step.
18. As a 教师, I want the paper built from the confirmed 考查范围, the 出卷需求, and the definitions / 解题步骤 / 教学重点 in the 材料, so that the paper fits this course.
19. As a 教师, I want every item on the 试卷 to be a 题目 already in the 题库, so that unreviewed model text never appears as a scored question.
20. As a 教师, I want a 题目草稿 for each shortfall in type counts, so that missing items are visible instead of silently inserted.
21. As a 教师, I want to accept, edit-then-accept, or reject a 题目草稿, so that only I decide what enters the 题库.
22. As a 教师, I want accepting a 题目草稿 to vectorize it and make it a 题目, so that later 组卷 can use it.
23. As a 教师, I want to preview the 试卷, so that I can read it before class.
24. As a 教师, I want to change stem, options, answer, explanation, score and order on the 试卷, so that I can fix issues without regenerating everything.
25. As a 教师, I want to replace one 试卷 item with another 题目 of the same type from the 题库, so that I can swap a weak question.
26. As a 教师, I want to save the 试卷, so that I can come back to it.
27. As a 教师, I want to export the 试卷 as DOCX / PDF / TXT with or without answers, so that I can print or archive it.
28. As a 教师, I want to export an answer sheet, so that marking on paper is aligned with question numbers.
29. As a 教师, I want to list, open and delete saved 试卷, so that old sittings do not clutter the workspace.
30. As a 教师, I want to search the 题库 by type, difficulty, chapter and meaning, so that I can find items without scrolling.
31. As a 教师, I want to add, edit, delete and batch-import 题目, so that the 题库 can be maintained by hand.
32. As a 教师, I want the 教学助手 to search 题目, propose 组卷 and answer course questions, so that I can work in language as well as forms.
33. As a 教师, I want 教学助手 组卷 to produce a 考查范围 I must confirm, then a 试卷 and any 题目草稿, so that chat cannot bypass the same rules as the form.
34. As a 教师, I want a disconnected 教学助手 thread to resume, so that a long 组卷 is not lost.
35. As a 教师, I want the same pages as today (home, 材料, 知识树, 题库, 组卷, 试卷, export, 教学助手) rewritten in the new frontend, so that I am not learning a new product, only a completed one.
36. As a 教师, I want 题目草稿 and 考查范围 as the only new screens, so that the rest of the work is completing the basic requirements rather than adding side products.

## Implementation Decisions

- Frontend is React 18 + TypeScript + Vite + Ant Design 5 + React Router + Zustand. No Vue, no Naive UI in the running app.
- Backend stays FastAPI + SQLAlchemy async + aiosqlite + Chroma + DeepSeek Chat + local `BAAI/bge-small-zh-v1.5` + LangGraph. Python 3.10 compatible (sync graph nodes if interrupt still requires it).
- Running app lives at repo-root `backend/` and `frontend/`. Current tree is frozen under `baselines/` then removed from the running path. Local SQLite / Chroma / checkpoints may be rebuilt. Course PPT files are kept and re-importable.
- 材料 has a kind: `lecture_notes` (教案), `slides` (PPT), `syllabus` (大纲), `other`. Accepted files remain pptx / docx / pdf / md.
- 知识节点 at point level stores definition, key_terms, teaching_emphasis, solution_steps, source_text. Extraction prompt must fill all of these from the 材料 and must not invent.
- 出卷需求 fields: title, duration, total_score, teaching_progress, exam_scope, question_distribution, difficulty_distribution, focus_notes, optional material_ids.
- 考查范围 is persisted (scope row + scope nodes). Status is `proposed` or `confirmed`. 组卷 API refuses `proposed`.
- ScopeBuilder builds the 考查范围 from course 知识树 + 出卷需求 (progress, scope text, focus, selected materials). It filters and keeps tree shape; teacher edits are first-class.
- PaperAssembler is the only 组卷 implementation. It retrieves 题目 with RAG constrained by confirmed 考查范围 and 出卷需求, ranks/trims to type counts, and writes 题目草稿 on shortfall. It never inserts a 题目.
- QuestionAuthor is an internal seam used only to propose 题目草稿. Production adapter calls DeepSeek with 材料 definition / 解题步骤 / 教学重点 as context. Tests inject a fake.
- Confirming a 题目草稿 creates a 题目, embeds it, and does not put it on a 试卷 by itself.
- `POST /api/exams/generate` requires a confirmed 考查范围 id. Response includes exam_id, questions, drafts, shortfall.
- `POST /api/scopes/propose` creates a proposed 考查范围. `PUT /api/scopes/{id}` edits nodes. `POST /api/scopes/{id}/confirm` flips status.
- `GET/POST /api/drafts` list and create-from-internal-only; `POST /api/drafts/{id}/accept`; `POST /api/drafts/{id}/reject`; `PUT /api/drafts/{id}` for edit-before-accept.
- Delete `/api/chat` function-calling path. `POST /api/chat` is the LangGraph graph. Graph: router → search | knowledge | propose_scope → scope interrupt → assemble → paper interrupt → chat. Resume payloads distinguish scope confirm vs paper confirm.
- Verify / regenerate / auto-fix only use the 题库. If still short, they create 题目草稿, never 题目.
- knowledge_snapshot_json on 试卷 stores the confirmed 考查范围 tree copy at generate time.
- Primary test seams: ScopeBuilder.propose and PaperAssembler.assemble. HTTP tests cover confirm-required generate and draft accept. No Vue component tests; frontend must `npm run build`.
- Difference gate: `scripts/measure_diff.py` against frozen baselines. Source churn, module replacement, and academic-doc rewrite each ≥ 30%. Academic four-pack (计划书、中期报告、开发文档、答辩 PPT) each rewritten with outline change + paragraph replacement ≥ 30%. Qualitative checklist must also pass (new stack, 考查范围, 题目草稿, no Vue as current stack).
- Core module inventory for the 30% module metric (replace or add counts as change): Material kind, Knowledge extract, ScopeBuilder, ExamScope persistence, PaperAssembler, QuestionDraft, Draft accept, Chat graph, Chat HTTP, Exam wizard UI, Knowledge tree UI, Material UI, Question bank UI, Exam preview/export UI, 教学助手 UI, Academic 计划书, Academic 中期报告, Academic 开发文档, Academic 答辩 PPT, Engineering README/CONTEXT/ADR. At least 30% of this inventory must be new or rewritten.
- Docs: rewrite 原文档 four-pack and engineering docs (README, CONTEXT already, ADRs, spec, AGENTS). Old `docs/superpowers` v2 specs are superseded, not patched.

## Testing Decisions

- Tests describe external behavior of ScopeBuilder and PaperAssembler, not LLM prompt wording or SQLAlchemy internals.
- ScopeBuilder: given a course tree and 出卷需求 that names one chapter, the proposed 考查范围 contains that chapter's points and not unrelated chapters; teacher-added nodes persist across propose/edit.
- PaperAssembler: bank count does not increase on shortfall; drafts length equals missing type counts; 试卷 items all have 题目 ids from the bank; assemble without confirmed scope raises.
- Draft accept: 题库 count +1, draft status accepted, embedding id set. Reject: 题库 unchanged.
- Generate HTTP: 403/400 if scope not confirmed.
- Prior art: the repo has no test suite today. New tests live next to backend as pytest + httpx AsyncClient. Do not add a Jest forest for page chrome.
- Measurement script has its own tests on synthetic directories so the 30% gate cannot be silently wrong.

## Out of Scope

- Student 答题、批改、错题本, login/roles, multi-tenant.
- Coverage-score product line, heatmap, exam timer.
- Changing backend web framework or vector database.
- Next.js, shadcn, Django, NestJS.
- Generating 题目 straight into the 题库 or onto the 试卷.
- Keeping Vue files in the running frontend.
- Migrating existing `ds_teaching.db` in place.
- Inventing knowledge not present in 材料.

## Further Notes

- 基础需求 is the product contract. 考查范围 and 题目草稿 are required to meet it; they are not optional extras.
- Previous decision “only 题目草稿 as a new object” is superseded by 考查范围, because 基础需求 items 4–5 are otherwise unmet.
- Implementing agent reads CONTEXT.md, docs/adr, this spec, and the plan together. Review later uses this spec as the Spec axis and the ADRs plus CONTEXT as the Standards axis.
- Seams to test: ScopeBuilder.propose and PaperAssembler.assemble. If those two hold, the basic requirements 4–7 can be verified without opening the UI.
