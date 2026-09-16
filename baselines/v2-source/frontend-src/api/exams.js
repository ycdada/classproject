import api from './index.js'

export const examApi = {
  generate(requirements) {
    // 组卷涉及两次串行 LLM 调用（缺题生成 + 组卷筛选），耗时不定，单独放宽超时
    return api.post('/exams/generate', requirements, { timeout: 300000 })
  },
  list() {
    return api.get('/exams')
  },
  get(id) {
    return api.get(`/exams/${id}`)
  },
  replaceQuestion(examId, eqId, data) {
    return api.put(`/exams/${examId}/questions/${eqId}`, data)
  },
  exportExam(examId, options = {}) {
    const withAnswer = typeof options === 'boolean' ? options : (options.withAnswer || false)
    const format = (typeof options === 'object' && options.format) || 'docx'
    return api.get(`/exams/${examId}/export`, {
      params: { with_answer: withAnswer, format },
      responseType: 'blob',
      timeout: 60000,
    })
  },
  evaluate(examId) {
    // AI 评价是一次完整 LLM 调用，放宽超时
    return api.post(`/exams/${examId}/evaluate`, null, { timeout: 120000 })
  },
  regenerateQuestion(examId, eqId) {
    return api.post(`/exams/${examId}/questions/${eqId}/regenerate`, null, { timeout: 60000 })
  },
  verify(examId, autoFix = true) {
    return api.post(`/exams/${examId}/verify?auto_fix=${autoFix}`)
  },
  answerSheet(examId) {
    return api.get(`/exams/${examId}/answer-sheet`, { responseType: 'blob', timeout: 60000 })
  },
  delete(id) {
    return api.delete(`/exams/${id}`)
  },
}
