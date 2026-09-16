<template>
  <n-form :model="form" label-placement="top">
    <n-grid :cols="2" :x-gap="12">
      <n-form-item-gi label="题型" required>
        <n-select v-model:value="form.type" :options="typeOptions" />
      </n-form-item-gi>
      <n-form-item-gi label="难度">
        <n-rate v-model:value="form.difficulty" :count="5" />
      </n-form-item-gi>
    </n-grid>
    <n-form-item label="知识点">
      <n-select v-model:value="form.knowledge_points" :options="knowledgeOptions" multiple filterable tag placeholder="选择或输入知识点" />
    </n-form-item>
    <n-form-item label="题干" required>
      <n-input v-model:value="form.content" type="textarea" :rows="3" placeholder="请输入题目内容" />
    </n-form-item>
    <n-form-item v-if="form.type === 'choice'" label="选项（每行一个，格式: A. 选项内容）">
      <n-input v-model:value="optionsText" type="textarea" :rows="4" placeholder="A. 选项A内容&#10;B. 选项B内容" />
    </n-form-item>
    <n-form-item label="答案" required>
      <n-input v-model:value="form.answer" type="textarea" :rows="2" :placeholder="answerPlaceholder" />
    </n-form-item>
    <n-form-item label="解析">
      <n-input v-model:value="form.explanation" type="textarea" :rows="3" placeholder="解题思路或知识点解析" />
    </n-form-item>
    <n-form-item label="标签">
      <n-select v-model:value="form.tags" :options="tagOptions" multiple filterable tag placeholder="自定义标签" />
    </n-form-item>
    <n-space justify="end">
      <n-button @click="$emit('cancel')">取消</n-button>
      <n-button type="primary" @click="handleSubmit" :disabled="!isValid">提交</n-button>
    </n-space>
  </n-form>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { QUESTION_TYPES, KNOWLEDGE_POINTS } from '../utils/constants.js'

const emit = defineEmits(['submit', 'cancel'])

const typeOptions = Object.entries(QUESTION_TYPES).map(([value, label]) => ({ label, value }))
const knowledgeOptions = KNOWLEDGE_POINTS.map(kp => ({ label: kp, value: kp }))
const tagOptions = [
  ...KNOWLEDGE_POINTS.map(kp => ({ label: kp, value: kp })),
  { label: '基础', value: '基础' },
  { label: '进阶', value: '进阶' },
  { label: '综合', value: '综合' },
]

const form = reactive({
  type: 'choice',
  difficulty: 3,
  knowledge_points: [],
  content: '',
  answer: '',
  explanation: '',
  source: 'manual',
  tags: [],
})
const optionsText = ref('')

const answerPlaceholder = computed(() => {
  const hints = {
    choice: '如: A',
    fill: '如: O(nlogn)',
    tf: '如: 正确',
    short_answer: '如: 详细解答...',
    code: '如: void func() { ... }',
  }
  return hints[form.type] || '请输入答案'
})

const isValid = computed(() => {
  return form.type && form.difficulty && form.content.trim() && form.answer.trim()
})

function handleSubmit() {
  const data = { ...form }
  if (data.type === 'choice' && optionsText.value.trim()) {
    data.options = optionsText.value.split('\n').filter(s => s.trim())
  }
  emit('submit', data)
}
</script>
