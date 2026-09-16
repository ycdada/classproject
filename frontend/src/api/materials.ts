import type { Material, MaterialKind } from '../types'
import { api } from './client'

export async function uploadMaterial(file: File, kind: MaterialKind, chapter?: number): Promise<Material> {
  const form = new FormData()
  form.append('file', file)
  form.append('kind', kind)
  if (chapter != null) form.append('chapter', String(chapter))
  const res = await api.post<Material>('/materials/upload', form)
  return res.data
}

export async function listMaterials(): Promise<Material[]> {
  const res = await api.get<Material[]>('/materials')
  return res.data
}

export async function getMaterial(id: number): Promise<Material> {
  const res = await api.get<Material>(`/materials/${id}`)
  return res.data
}

export async function deleteMaterial(id: number): Promise<void> {
  await api.delete(`/materials/${id}`)
}
