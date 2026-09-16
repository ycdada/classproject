import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: () => import('../views/teacher/Dashboard.vue') },
  { path: '/questions', component: () => import('../views/teacher/QuestionBank.vue') },
  { path: '/materials/upload', component: () => import('../views/teacher/MaterialUpload.vue') },
  { path: '/materials/:id', component: () => import('../views/teacher/MaterialDetail.vue') },
  { path: '/knowledge', redirect: '/knowledge/1' },
  { path: '/knowledge/:materialId', component: () => import('../views/teacher/KnowledgeTree.vue') },
  { path: '/exams', component: () => import('../views/teacher/ExamList.vue') },
  { path: '/exams/create', component: () => import('../views/teacher/ExamWizard.vue') },
  { path: '/exams/:id/review', component: () => import('../views/teacher/ExamReview.vue') },
  { path: '/exams/:id', component: () => import('../views/teacher/ExamPreview.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
