<template>
  <div class="exam-card">
    <div class="exam-card__header">📝 试卷已生成</div>
    <p v-if="data.summary">{{ data.summary }}</p>
    <n-space>
      <n-button type="primary" size="small" @click="handlePreview">
        预览试卷
      </n-button>
      <n-button size="small" @click="exportDocx">导出 Word</n-button>
    </n-space>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({ data: Object })
const emit = defineEmits(['previewExam'])
const router = useRouter()

function handlePreview() {
  const examId = props.data?.exam_id || props.data?.id
  if (examId) {
    router.push(`/exams/${examId}`)
  }
}

function exportDocx() {
  const examId = props.data?.exam_id || props.data?.id
  if (examId) {
    window.open(`/api/exams/${examId}/export`, '_blank')
  }
}
</script>

<style scoped>
.exam-card {
  padding: 4px 0;
}
.exam-card__header {
  font-weight: 600;
  margin-bottom: 8px;
}
.exam-card p {
  font-size: 13px;
  color: #666;
  margin: 4px 0 8px;
}
</style>
