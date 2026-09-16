<template>
  <div style="max-width: 900px; margin: 0 auto;">
    <n-space justify="space-between" style="margin-bottom: 16px;">
      <n-h2 style="margin: 0;">{{ exam?.title }}</n-h2>
      <n-space>
        <n-button @click="$router.push('/dashboard')">返回首页</n-button>
        <n-dropdown trigger="click" :options="formatOptions" @select="(f) => exportExam(false, f)">
          <n-button>导出试卷 ▾</n-button>
        </n-dropdown>
        <n-dropdown trigger="click" :options="formatOptions" @select="(f) => exportExam(true, f)">
          <n-button type="info">导出(含答案) ▾</n-button>
        </n-dropdown>
        <n-button type="warning" @click="exportSheet" :loading="sheetLoading">📝 答题卡</n-button>
        <n-button @click="$router.push('/exams')">返回列表</n-button>
      </n-space>
    </n-space>

    <n-spin :show="loading">
      <n-space justify="center" style="margin-bottom: 12px;">
        <n-tag>总分: {{ exam?.total_score }}分</n-tag>
        <n-tag>时长: {{ exam?.duration }}分钟</n-tag>
        <n-tag :type="exam?.status === 'exported' ? 'success' : 'warning'">
          {{ exam?.status }}
        </n-tag>
      </n-space>

      <n-empty v-if="!exam?.questions?.length" description="暂无题目" />
      <n-space v-else vertical :size="12">
        <n-card v-for="(q, idx) in exam.questions" :key="q.eq_id" size="small"
          :title="`第 ${idx + 1} 题 (${q.score}分) [${typeName(q.type)}]`">
          <p style="font-size: 15px; white-space: pre-wrap;">{{ q.content }}</p>
          <p v-if="q.options" v-for="(opt, oi) in q.options" :key="oi" style="margin: 2px 0 2px 20px;">
            {{ typeof oi === 'string' ? `${oi}. ${opt}` : opt }}
          </p>
          <n-collapse>
            <n-collapse-item title="查看答案">
              <n-text type="success" style="white-space: pre-wrap;">答案: {{ q.answer }}</n-text>
              <n-text v-if="q.explanation" depth="3" style="display: block; margin-top: 4px; white-space: pre-wrap;">
                解析: {{ q.explanation }}
              </n-text>
            </n-collapse-item>
          </n-collapse>
        </n-card>
      </n-space>
    </n-spin>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { examApi } from '../../api/exams.js'

const route = useRoute()
const message = useMessage()
const exam = ref(null)
const loading = ref(false)
const sheetLoading = ref(false)

const TYPE_NAMES = { choice: '选择', fill: '填空', tf: '判断', short_answer: '简答', code: '算法设计' }
const typeName = (t) => TYPE_NAMES[t] || t

const formatOptions = [
  { label: 'Word (.docx)', key: 'docx' },
  { label: 'PDF (.pdf)', key: 'pdf' },
  { label: '纯文本 (.txt)', key: 'txt' },
]

onMounted(async () => {
  loading.value = true
  try {
    const res = await examApi.get(route.params.id)
    exam.value = res.data
  } catch (e) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
})

async function exportExam(withAnswer, format = 'docx') {
  try {
    const res = await examApi.exportExam(route.params.id, { withAnswer, format })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `${exam.value.title}${withAnswer ? '(含答案)' : ''}.${format}`
    a.click()
    window.URL.revokeObjectURL(url)
    message.success('导出成功')
  } catch (e) {
    message.error('导出失败')
  }
}

async function exportSheet() {
  sheetLoading.value = true
  try {
    const res = await examApi.answerSheet(route.params.id)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `${exam.value?.title}_答题卡.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
    message.success('答题卡导出成功')
  } catch (e) {
    message.error('答题卡导出失败')
  } finally { sheetLoading.value = false }
}
</script>
