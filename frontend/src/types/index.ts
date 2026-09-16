// 领域类型 — 与后端 schema 字段同名（CONTEXT.md 领域词）
export interface Material {
  id: number
  filename: string
  file_type: string
  kind: MaterialKind
  chapter: number | null
  page_count: number
  uploaded_at: string
  content_md?: string | null
}

export type MaterialKind = 'lecture_notes' | 'slides' | 'syllabus' | 'other'

export interface KnowledgeNode {
  id: number
  material_id: number
  parent_id: number | null
  sort_order: number
  name: string
  node_type: 'chapter' | 'section' | 'point'
  definition: string | null
  key_terms: string[] | null
  teaching_emphasis: string | null
  solution_steps: string | null
  children: KnowledgeNode[]
}

// 出卷需求（教师本次组卷的输入）
export interface ExamDemand {
  title: string
  duration: number
  total_score: number
  teaching_progress: string
  exam_scope: string
  focus_notes: string
  material_ids: number[]
  knowledge_node_ids?: number[]
  scope_id?: number
  question_distribution: Record<string, number>
  difficulty_distribution: Record<string, number>
}

// 考查范围（教师审核、修改并确认后才能组卷）
export interface ExamScopeNode {
  id: number
  scope_id: number
  parent_id: number | null
  source_node_id: number | null
  sort_order: number
  name: string
  node_type: 'chapter' | 'section' | 'point'
  definition: string | null
  key_terms: string[] | null
  teaching_emphasis: string | null
  solution_steps: string | null
  included: boolean
  children: ExamScopeNode[]
}

export interface ExamScope {
  id: number
  status: 'proposed' | 'confirmed'
  demand: ExamDemand | null
  tree: ExamScopeNode[]
}

export interface Question {
  id: number
  type: QuestionType
  difficulty: number
  chapter: string | null
  knowledge_point_ids: string[]
  content: string
  options: Record<string, string> | null
  answer: string
  explanation: string | null
  source: string
  embedding_id?: string | null
  created_at?: string
}

export type QuestionType = 'choice' | 'fill' | 'tf' | 'short_answer' | 'code'

// 题目草稿（教师确认前不是题目）
export interface QuestionDraft {
  id: number
  type: QuestionType
  difficulty: number
  chapter: string | null
  knowledge_point_ids: string[]
  content: string
  options: Record<string, string> | null
  answer: string
  explanation: string | null
  status: 'pending' | 'accepted' | 'rejected'
  exam_scope_id: number | null
  created_at: string
}

export interface Exam {
  id: number
  title: string
  created_by: string
  status: 'draft' | 'reviewed' | 'exported'
  total_score: number
  duration: number
  created_at: string
  questions: ExamQuestionItem[]
}

export interface ExamQuestionItem {
  eq_id: number
  question_id: number | null
  score: number
  sort_order: number
  type: string
  content: string
  options: Record<string, string> | null
  answer: string
  explanation: string
}

// 组卷结果：题库题 + 缺口草稿
export interface AssembleResponse {
  exam_id: number
  question_count: number
  drafts: Array<{ id: number; type: string; content: string; status: string }>
  shortfall: Record<string, number>
  summary: string
}
