<template>
  <div style="max-width: 800px; margin: 0 auto;">
    <n-space style="margin-bottom: 16px;">
      <n-button text @click="$router.push('/dashboard')">
        <template #icon><n-icon><arrow-back-outline /></n-icon></template>
        返回首页
      </n-button>
    </n-space>
    <n-h2 style="margin-bottom: 16px;">试卷导出</n-h2>
    <n-spin :show="loading">
      <n-card v-if="exam" :title="exam.title">
        <template #header-extra>
          <n-tag :type="exam.status === 'ready' ? 'success' : 'warning'">
            {{ exam.status === 'ready' ? '就绪' : '草稿' }}
          </n-tag>
        </template>
        <n-descriptions bordered :columns="2">
          <n-descriptions-item label="总分">{{ exam.total_score }}分</n-descriptions-item>
          <n-descriptions-item label="时长">{{ exam.duration }}分钟</n-descriptions-item>
          <n-descriptions-item label="题目数">{{ exam.questions?.length || 0 }}道</n-descriptions-item>
          <n-descriptions-item label="创建时间">{{ exam.created_at?.slice(0, 10) }}</n-descriptions-item>
        </n-descriptions>

        <n-divider>题目概览</n-divider>
        <n-ol>
          <n-li v-for="q in exam.questions" :key="q.eq_id || q.question_id" style="margin-bottom: 4px;">
            {{ (q.content || '').slice(0, 60) || `题目 #${q.question_id}` }}
            <n-tag size="tiny" :bordered="false">{{ q.score }}分</n-tag>
          </n-li>
        </n-ol>

        <n-divider>下载选项</n-divider>
        <n-space justify="center" :size="16">
          <n-button type="primary" size="large" @click="downloadWord(false)">
            <template #icon><n-icon><document-text-outline /></n-icon></template>
            Word (学生版)
          </n-button>
          <n-button type="info" size="large" @click="downloadWord(true)">
            <template #icon><n-icon><document-text-outline /></n-icon></template>
            Word (含答案)
          </n-button>
        </n-space>
      </n-card>
      <n-empty v-else description="试卷未找到" />
    </n-spin>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { DocumentTextOutline, ArrowBackOutline } from '@vicons/ionicons5'
import { examApi } from '../../api/exams.js'

const route = useRoute()
const exam = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await examApi.get(route.params.id)
    exam.value = res.data
  } finally {
    loading.value = false
  }
})

async function downloadWord(withAnswer) {
  try {
    const res = await examApi.exportExam(route.params.id, withAnswer)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `${exam.value.title}${withAnswer ? '_含答案' : ''}.docx`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    console.error('Export failed:', e)
  }
}
</script>
