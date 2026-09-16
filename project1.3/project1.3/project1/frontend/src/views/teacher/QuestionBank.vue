<template>
  <div style="max-width: 1400px; margin: 0 auto;">
    <n-space justify="space-between" align="center" style="margin-bottom: 16px;">
      <n-h2 style="margin: 0;">题库管理</n-h2>
      <n-space>
        <n-button type="primary" @click="openCreate">
          <template #icon><n-icon><add-outline /></n-icon></template>
          添加题目
        </n-button>
        <n-button @click="$router.push('/teacher/questions/import')">
          <template #icon><n-icon><cloud-upload-outline /></n-icon></template>
          批量导入
        </n-button>
      </n-space>
    </n-space>

    <n-card size="small" style="margin-bottom: 16px;">
      <n-space align="center">
        <n-select v-model:value="filters.type" :options="typeOptions" placeholder="题型" clearable style="width: 120px;" />
        <n-select v-model:value="filters.difficulty" :options="diffOptions" placeholder="难度" clearable style="width: 100px;" />
        <n-select v-model:value="filters.knowledge_point" :options="kpOptions" placeholder="知识点" clearable filterable style="width: 180px;" />
        <n-button type="primary" @click="search">搜索</n-button>
        <n-button @click="resetFilters">重置</n-button>
      </n-space>
    </n-card>

    <n-data-table
      :columns="columns"
      :data="store.questions"
      :loading="store.loading"
      :pagination="pagination"
      :row-key="(row) => row.id"
      striped
      style="background: var(--n-color);"
    />

    <n-modal v-model:show="showModal" :title="editingId ? '编辑题目' : '添加题目'" style="width: 800px;" preset="card">
      <QuestionForm
        v-if="showModal"
        ref="questionFormRef"
        @submit="handleSubmit"
        @cancel="showModal = false"
      />
    </n-modal>
  </div>
</template>

<script setup>
import { reactive, ref, h, onMounted } from 'vue'
import { NButton, NTag, NSpace, NPopconfirm, useMessage } from 'naive-ui'
import { AddOutline, CloudUploadOutline } from '@vicons/ionicons5'
import { useQuestionStore } from '../../stores/questions.js'
import { QUESTION_TYPES, DIFFICULTY_COLORS, KNOWLEDGE_POINTS } from '../../utils/constants.js'
import KnowledgeTag from '../../components/KnowledgeTag.vue'
import DifficultyStars from '../../components/DifficultyStars.vue'
import QuestionForm from '../../components/QuestionForm.vue'

const store = useQuestionStore()
const message = useMessage()
const showModal = ref(false)
const editingId = ref(null)
const questionFormRef = ref(null)

const filters = reactive({ type: null, difficulty: null, knowledge_point: null })

const typeOptions = Object.entries(QUESTION_TYPES).map(([value, label]) => ({ label, value }))
const diffOptions = [1, 2, 3, 4, 5].map(v => ({ label: '★'.repeat(v) + '☆'.repeat(5 - v), value: v }))
const kpOptions = KNOWLEDGE_POINTS.map(kp => ({ label: kp, value: kp }))

const pagination = reactive({
  page: 1,
  pageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
  itemCount: 0,
  prefix: (info) => `共 ${info.itemCount} 题`,
  onChange: (page) => { pagination.page = page; search() },
  onUpdatePageSize: (pageSize) => { pagination.pageSize = pageSize; pagination.page = 1; search() },
})

const columns = [
  { title: 'ID', key: 'id', width: 60, align: 'center' },
  {
    title: '题型', key: 'type', width: 80, align: 'center',
    render: (row) => h(NTag, { size: 'small', type: typeColor(row.type) }, { default: () => QUESTION_TYPES[row.type] || row.type }),
  },
  {
    title: '难度', key: 'difficulty', width: 130, align: 'center',
    render: (row) => h(DifficultyStars, { difficulty: row.difficulty }),
  },
  {
    title: '知识点', key: 'knowledge_points', width: 220,
    render: (row) => h(KnowledgeTag, { points: row.knowledge_points?.slice(0, 4) || [] }),
  },
  { title: '题干', key: 'content', ellipsis: { tooltip: true }, minWidth: 200 },
  {
    title: '来源', key: 'source', width: 60, align: 'center',
    render: (row) => h(NTag, { size: 'tiny', type: row.source === 'llm' ? 'success' : 'default' }, { default: () => row.source === 'llm' ? 'AI' : '人工' }),
  },
  {
    title: '操作', key: 'actions', width: 140, align: 'center',
    render: (row) => h(NSpace, { justify: 'center' }, {
      default: () => [
        h(NButton, { size: 'tiny', onClick: () => openEdit(row) }, { default: () => '编辑' }),
        h(NPopconfirm, { onPositiveClick: () => handleDelete(row.id) }, {
          trigger: () => h(NButton, { size: 'tiny', type: 'error' }, { default: () => '删除' }),
          default: () => `确认删除 ID:${row.id} 这道题目？`,
        }),
      ],
    }),
  },
]

function typeColor(type) {
  const map = { choice: 'primary', fill: 'info', tf: 'warning', short_answer: 'success', code: 'error' }
  return map[type] || 'default'
}

function search() {
  store.fetchQuestions({ ...filters, page: pagination.page, page_size: pagination.pageSize }).then(data => {
    pagination.itemCount = data.total
  })
}

function resetFilters() {
  filters.type = null
  filters.difficulty = null
  filters.knowledge_point = null
  pagination.page = 1
  search()
}

function openCreate() {
  editingId.value = null
  showModal.value = true
}

function openEdit(row) {
  editingId.value = row.id
  showModal.value = true
  // TODO: pre-fill form with row data in future iteration
}

async function handleSubmit(data) {
  try {
    if (editingId.value) {
      await store.editQuestion(editingId.value, data)
      message.success('更新成功')
    } else {
      await store.addQuestion(data)
      message.success('添加成功')
    }
    showModal.value = false
    editingId.value = null
    search()
  } catch (e) {
    message.error('操作失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function handleDelete(id) {
  try {
    await store.removeQuestion(id)
    message.success('删除成功')
    search()
  } catch (e) {
    message.error('删除失败')
  }
}

onMounted(() => search())
</script>
