import type { Question, QuestionType } from '../types'
import { api } from './client'

export interface QuestionListResult {
  items: Question[]
  total: number
}

export async function listQuestions(params: {
  page?: number
  page_size?: number
  type?: QuestionType
  difficulty?: number
  chapter?: string
  keyword?: string
}): Promise<QuestionListResult> {
  const res = await api.get<{ items: Question[]; total: number }>('/questions', { params })
  return res.data
}

export async function createQuestion(data: Partial<Question>): Promise<Question> {
  const res = await api.post<Question>('/questions', data)
  return res.data
}

export async function updateQuestion(id: number, data: Partial<Question>): Promise<Question> {
  const res = await api.put<Question>(`/questions/${id}`, data)
  return res.data
}

export async function deleteQuestion(id: number): Promise<void> {
  await api.delete(`/questions/${id}`)
}

export async function searchQuestions(query: string, topK = 20): Promise<Array<Record<string, unknown>>> {
  const res = await api.get('/questions/search', { params: { query, top_k: topK } })
  return res.data
}

export async function importQuestions(rows: Array<Partial<Question>>): Promise<unknown> {
  const res = await api.post('/questions/batch-import', { questions: rows })
  return res.data
}
