import type { ExamDemand, ExamScope, ExamScopeNode } from '../types'
import { api } from './client'

export async function proposeScope(demand: ExamDemand): Promise<ExamScope> {
  const res = await api.post<ExamScope>('/scopes/propose', demand)
  return res.data
}

export async function getScope(id: number): Promise<ExamScope> {
  const res = await api.get<ExamScope>(`/scopes/${id}`)
  return res.data
}

export async function updateScopeNode(
  scopeId: number,
  nodeId: number,
  data: Partial<Pick<ExamScopeNode, 'name' | 'definition' | 'key_terms' | 'teaching_emphasis' | 'solution_steps' | 'included'>>,
): Promise<void> {
  await api.put(`/scopes/${scopeId}/nodes/${nodeId}`, data)
}

export async function addScopeNode(
  scopeId: number,
  data: { parent_id?: number | null; name: string; node_type: string; definition?: string | null; included?: boolean },
): Promise<ExamScopeNode> {
  const res = await api.post<ExamScopeNode>(`/scopes/${scopeId}/nodes`, data)
  return res.data
}

export async function deleteScopeNode(scopeId: number, nodeId: number): Promise<void> {
  await api.delete(`/scopes/${scopeId}/nodes/${nodeId}`)
}

export async function confirmScope(scopeId: number): Promise<ExamScope> {
  const res = await api.post<ExamScope>(`/scopes/${scopeId}/confirm`)
  return res.data
}
