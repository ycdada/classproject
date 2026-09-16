import { defineStore } from 'pinia'
import { ref } from 'vue'
import { examApi } from '../api/exams.js'

export const useExamStore = defineStore('exams', () => {
  const exams = ref([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchExams(params = {}) {
    loading.value = true
    try {
      const res = await examApi.list()
      exams.value = res.data
      total.value = res.data.length
      return { items: res.data, total: res.data.length }
    } finally {
      loading.value = false
    }
  }

  async function removeExam(id) {
    await examApi.delete(id)
  }

  return { exams, total, loading, fetchExams, removeExam }
})
