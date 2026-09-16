import api from './index.js'

export const knowledgeApi = {
  extract(materialId) {
    return api.post(`/knowledge/extract/${materialId}`)
  },
  getTree(materialId) {
    return api.get(`/knowledge/tree/${materialId}`)
  },
  updateNode(nodeId, data) {
    return api.put(`/knowledge/nodes/${nodeId}`, data)
  },
  deleteTree(materialId) {
    return api.delete(`/knowledge/tree/${materialId}`)
  },
}
