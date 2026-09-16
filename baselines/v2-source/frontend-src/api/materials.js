import api from './index.js'

export const materialApi = {
  upload(formData) {
    return api.post('/materials/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  list() {
    return api.get('/materials')
  },
  get(id) {
    return api.get(`/materials/${id}`)
  },
  delete(id) {
    return api.delete(`/materials/${id}`)
  },
}
