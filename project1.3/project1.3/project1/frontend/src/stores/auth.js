import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    teacher: { name: '教师', id: 'teacher-001' },
  }),
  getters: {
    currentUser: (state) => state.teacher,
  },
})
