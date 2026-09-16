import type { AssembleResponse, Exam, ExamDemand } from '../types'
import { api, ASSEMBLE_TIMEOUT_MS } from './client'

export async function generateExam(demand: ExamDemand): Promise<AssembleResponse> {
  const res = await api.post<AssembleResponse>('/exams/generate', demand, {
    timeout: ASSEMBLE_TIMEOUT_MS,
  })
  return res.data
}

export async function listExams(): Promise<Exam[]> {
  const res = await api.get<Exam[]>('/exams')
  return res.data
}

export async function getExam(id: number): Promise<Exam> {
  const res = await api.get<Exam>(`/exams/${id}`)
  return res.data
}

export async function updateExamQuestion(
  examId: number,
  eqId: number,
  data: Record<string, unknown>,
): Promise<void> {
  await api.put(`/exams/${examId}/questions/${eqId}`, data)
}

export async function verifyExam(examId: number, autoFix = false): Promise<Record<string, unknown>> {
  const res = await api.post(`/exams/${examId}/verify?auto_fix=${autoFix}`)
  return res.data
}

export async function exportExam(examId: number, format: 'docx' | 'pdf' | 'txt', withAnswer: boolean): Promise<void> {
  const res = await api.get(`/exams/${examId}/export`, {
    params: { format, with_answer: withAnswer },
    responseType: 'blob',
  })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  const dispo = res.headers['content-disposition'] as string | undefined
  const star = dispo?.match(/filename\*=UTF-8''([^;]+)/)
  const plain = dispo?.match(/filename="([^"]+)"/)
  let name = `exam_${examId}.${format}`
  try {
    if (star) name = decodeURIComponent(star[1])
    else if (plain) name = plain[1]
  } catch {
    /* keep fallback */
  }
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

export async function exportAnswerSheet(examId: number): Promise<void> {
  const res = await api.get(`/exams/${examId}/answer-sheet`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = `answer_sheet_${examId}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

export async function deleteExam(examId: number): Promise<void> {
  await api.delete(`/exams/${examId}`)
}
