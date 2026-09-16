import api from './index.js'

export function getQuestions(params) {
  return api.get('/questions', { params })
}

export function getQuestion(id) {
  return api.get(`/questions/${id}`)
}

export function createQuestion(data) {
  return api.post('/questions', data)
}

export function updateQuestion(id, data) {
  return api.put(`/questions/${id}`, data)
}

export function deleteQuestion(id) {
  return api.delete(`/questions/${id}`)
}

export function batchImportQuestions(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/questions/batch-import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
