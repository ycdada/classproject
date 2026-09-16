import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

export const ASSEMBLE_TIMEOUT_MS = 300000

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err?.response?.data?.detail
    if (detail) {
      err.message = typeof detail === 'string' ? detail : JSON.stringify(detail)
    }
    return Promise.reject(err)
  },
)
