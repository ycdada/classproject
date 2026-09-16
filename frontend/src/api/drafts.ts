import type { QuestionDraft } from '../types'
import { api } from './client'

export async function listDrafts(status?: QuestionDraft['status']): Promise<QuestionDraft[]> {
  const res = await api.get<QuestionDraft[]>('/drafts', { params: status ? { status } : {} })
  return res.data
}

export async function updateDraft(id: number, data: Partial<QuestionDraft>): Promise<QuestionDraft> {
  const res = await api.put<QuestionDraft>(`/drafts/${id}`, data)
  return res.data
}

export async function acceptDraft(id: number): Promise<{ question_id: number }> {
  const res = await api.post(`/drafts/${id}/accept`)
  return res.data
}

export async function rejectDraft(id: number): Promise<QuestionDraft> {
  const res = await api.post<QuestionDraft>(`/drafts/${id}/reject`)
  return res.data
}
