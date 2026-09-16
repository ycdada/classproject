<template>
  <div style="max-width: 800px; margin: 0 auto;">
    <n-h2 style="margin-bottom: 16px;">组卷编辑器</n-h2>
    <n-card>
      <n-form :model="form" label-placement="top">
        <n-form-item label="试卷名称" required>
          <n-input v-model:value="form.title" placeholder="如: 数据结构期中考试" />
        </n-form-item>
        <n-grid :cols="2" :x-gap="16">
          <n-form-item-gi label="总分">
            <n-input-number v-model:value="form.total_score" :min="10" :max="200" />
          </n-form-item-gi>
          <n-form-item-gi label="考试时长(分钟)">
            <n-input-number v-model:value="form.duration" :min="10" :max="300" />
          </n-form-item-gi>
        </n-grid>
        <n-form-item label="题目数量">
          <n-slider v-model:value="form.question_count" :min="5" :max="50" :step="5" :marks="countMarks" />
        </n-form-item>
        <n-divider>题型分布 (%)</n-divider>
        <n-grid :cols="5" :x-gap="8">
          <n-form-item-gi v-for="t in types" :key="t.key" :label="t.label">
            <n-input-number v-model:value="form.type_distribution[t.key]" :min="0" :max="100" size="small" />
          </n-form-item-gi>
        </n-grid>
        <n-divider>难度分布 (%)</n-divider>
        <n-grid :cols="5" :x-gap="8">
          <n-form-item-gi v-for="d in 5" :key="d" :label="'★'.repeat(d)">
            <n-input-number v-model:value="form.difficulty_distribution[d]" :min="0" :max="100" size="small" />
          </n-form-item-gi>
        </n-grid>
        <n-form-item label="知识点范围">
          <n-select v-model:value="form.knowledge_points" :options="kpOptions" multiple filterable tag placeholder="选择或输入知识点" />
        </n-form-item>
        <n-space justify="center" style="margin-top: 24px;">
          <n-button @click="$router.back()">取消</n-button>
          <n-button type="primary" @click="handleGenerate" :loading="generating">
            <template #icon><n-icon><flash-outline /></n-icon></template>
            自动组卷
          </n-button>
        </n-space>
      </n-form>
    </n-card>

    <n-modal v-model:show="showResult" title="组卷完成" preset="card" style="width: 600px;">
      <n-result v-if="generatedExam" status="success" :title="`「${generatedExam.title}」已生成`" :description="`共 ${generatedExam.questions?.length || 0} 道题目，总分 ${generatedExam.total_score} 分`">
        <template #footer>
          <n-space justify="center">
            <n-button @click="showResult = false">继续编辑</n-button>
            <n-button type="primary" @click="$router.push(`/teacher/exams/${generatedExam.id}/export`)">导出试卷</n-button>
          </n-space>
        </template>
      </n-result>
    </n-modal>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { FlashOutline } from '@vicons/ionicons5'
import { useMessage } from 'naive-ui'
import { useExamStore } from '../../stores/exams.js'
import { useAuthStore } from '../../stores/auth.js'
import { KNOWLEDGE_POINTS } from '../../utils/constants.js'

const store = useExamStore()
const auth = useAuthStore()
const message = useMessage()
const generating = ref(false)
const showResult = ref(false)
const generatedExam = ref(null)
const kpOptions = KNOWLEDGE_POINTS.map(kp => ({ label: kp, value: kp }))
const types = [
  { key: 'choice', label: '选择题' },
  { key: 'fill', label: '填空题' },
  { key: 'tf', label: '判断题' },
  { key: 'short_answer', label: '简答题' },
  { key: 'code', label: '编程题' },
]

const countMarks = { 5: '5', 10: '10', 20: '20', 30: '30', 40: '40', 50: '50' }

const form = reactive({
  title: '数据结构测试',
  total_score: 100,
  duration: 120,
  question_count: 20,
  type_distribution: { choice: 40, fill: 20, tf: 10, short_answer: 20, code: 10 },
  difficulty_distribution: { 1: 10, 2: 20, 3: 40, 4: 20, 5: 10 },
  knowledge_points: [],
})

async function handleGenerate() {
  const totalTypePct = Object.values(form.type_distribution).reduce((a, b) => a + b, 0)
  const totalDiffPct = Object.values(form.difficulty_distribution).reduce((a, b) => a + b, 0)
  if (totalTypePct !== 100 && totalTypePct !== 0) {
    message.warning('题型分布合计应为100%')
    return
  }
  if (totalDiffPct !== 100 && totalDiffPct !== 0) {
    message.warning('难度分布合计应为100%')
    return
  }

  generating.value = true
  try {
    generatedExam.value = await store.generateExamPaper({
      ...form,
      created_by: auth.userId,
      difficulty_distribution: form.difficulty_distribution,
      type_distribution: form.type_distribution,
    })
    showResult.value = true
    message.success('组卷成功')
  } catch (e) {
    message.error('组卷失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    generating.value = false
  }
}
</script>
