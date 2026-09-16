import type { KnowledgeNode } from '../types'
import { api } from './client'

export async function extractTree(materialId: number): Promise<{ nodes_created: number }> {
  const res = await api.post(`/knowledge/extract/${materialId}`)
  return res.data
}

export async function getTree(materialId: number): Promise<KnowledgeNode[]> {
  const res = await api.get<KnowledgeNode[]>(`/knowledge/tree/${materialId}`)
  return res.data
}

export async function updateNode(
  nodeId: number,
  data: Partial<Pick<KnowledgeNode, 'name' | 'definition' | 'key_terms' | 'teaching_emphasis' | 'solution_steps' | 'sort_order'>>,
): Promise<void> {
  await api.put(`/knowledge/nodes/${nodeId}`, data)
}

export async function deleteTree(materialId: number): Promise<void> {
  await api.delete(`/knowledge/tree/${materialId}`)
}
