import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as questionApi from '../api/questions.js'

export const useQuestionStore = defineStore('questions', () => {
  const questions = ref([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchQuestions(params = {}) {
    loading.value = true
    try {
      const res = await questionApi.getQuestions(params)
      questions.value = res.data.items
      total.value = res.data.total
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function addQuestion(data) {
    const res = await questionApi.createQuestion(data)
    return res.data
  }

  async function editQuestion(id, data) {
    const res = await questionApi.updateQuestion(id, data)
    return res.data
  }

  async function removeQuestion(id) {
    await questionApi.deleteQuestion(id)
  }

  async function importFile(file) {
    const res = await questionApi.batchImportQuestions(file)
    return res.data
  }

  return { questions, total, loading, fetchQuestions, addQuestion, editQuestion, removeQuestion, importFile }
})
