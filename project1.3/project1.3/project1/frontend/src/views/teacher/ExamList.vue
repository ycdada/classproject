<template>
  <div style="max-width: 1200px; margin: 0 auto;">
    <n-space justify="space-between" align="center" style="margin-bottom: 16px;">
      <n-h2 style="margin: 0;">试卷管理</n-h2>
      <n-button type="primary" @click="$router.push('/exams/create')">
        <template #icon><n-icon><add-outline /></n-icon></template>
        新建试卷
      </n-button>
    </n-space>

    <n-data-table
      :columns="columns"
      :data="store.exams"
      :loading="store.loading"
      :pagination="pagination"
      :row-key="(row) => row.id"
      striped
    />
  </div>
</template>

<script setup>
import { reactive, h, onMounted } from 'vue'
import { NButton, NTag, NSpace, NPopconfirm, useMessage } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { useExamStore } from '../../stores/exams.js'
import { useRouter } from 'vue-router'

const store = useExamStore()
const router = useRouter()
const message = useMessage()

const pagination = reactive({
  page: 1, pageSize: 20, showSizePicker: true, pageSizes: [10, 20, 50],
  onChange: (page) => { pagination.page = page; search() },
  onUpdatePageSize: (s) => { pagination.pageSize = s; search() },
})

const columns = [
  { title: 'ID', key: 'id', width: 60, align: 'center' },
  { title: '试卷名称', key: 'title', ellipsis: { tooltip: true } },
  {
    title: '状态', key: 'status', width: 80, align: 'center',
    render: (row) => h(NTag, { type: row.status === 'ready' ? 'success' : 'warning', size: 'small' }, { default: () => row.status === 'ready' ? '就绪' : '草稿' }),
  },
  { title: '总分', key: 'total_score', width: 80, align: 'center' },
  { title: '时长(分)', key: 'duration', width: 80, align: 'center' },
  {
    title: '操作', key: 'actions', width: 200, align: 'center',
    render: (row) => h(NSpace, { justify: 'center' }, {
      default: () => [
        h(NButton, { size: 'tiny', onClick: () => router.push(`/exams/${row.id}`) }, { default: () => '预览' }),
        h(NPopconfirm, { onPositiveClick: () => handleDelete(row.id) }, {
          trigger: () => h(NButton, { size: 'tiny', type: 'error' }, { default: () => '删除' }),
          default: () => `确认删除"${row.title}"？`,
        }),
      ],
    }),
  },
]

function search() {
  store.fetchExams({ page: pagination.page, page_size: pagination.pageSize })
}

async function handleDelete(id) {
  await store.removeExam(id)
  message.success('删除成功')
  search()
}

onMounted(() => search())
</script>
