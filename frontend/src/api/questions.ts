import type { Question, QuestionType } from '../types'
import { api } from './client'

export interface QuestionListResult {
  items: Question[]
  total: number
}

export async function listQuestions(params: {
  page?: number
  page_size?: number
  qtype?: QuestionType
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
  const res = await api.post('/questions/search', { query, top_k: topK })
  return res.data
}

export async function importQuestions(rows: Array<Partial<Question>>): Promise<{ created: number }> {
  const res = await api.post('/questions/import', { questions: rows })
  return res.data
}
