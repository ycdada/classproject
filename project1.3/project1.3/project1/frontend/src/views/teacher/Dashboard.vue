<template>
  <div style="max-width: 1200px; margin: 0 auto;">
    <div class="dash-hero">
      <h1 class="dash-title">{{ greeting }}，准备出一份新试卷？</h1>
      <p class="dash-sub">上传课件 · 抽取知识树 · AI 组卷 · 一键导出</p>
      <n-space>
        <n-button type="primary" @click="$router.push('/materials/upload')">
          <template #icon><n-icon><cloud-upload-outline /></n-icon></template>
          上传课件
        </n-button>
        <n-button @click="$router.push('/exams/create')">新建试卷</n-button>
      </n-space>
    </div>

    <div class="dash-stats">
      <div class="stat-card">
        <b class="mono">{{ materials.length }}</b>
        <span>教学材料</span>
      </div>
      <div class="stat-card">
        <b class="mono">{{ questionTotal }}</b>
        <span>题库题目</span>
      </div>
      <div class="stat-card">
        <b class="mono">{{ exams.length }}</b>
        <span>已生成试卷</span>
      </div>
    </div>

    <!-- 上半部分：左右两栏 -->
    <n-grid cols="2" :x-gap="16" style="margin-bottom: 16px;">
      <n-grid-item>
        <n-card title="教学材料库" size="small">
          <template #header-extra>
            <n-space align="center" :size="8">
              <n-tag type="info" size="small">{{ materials.length }} 份</n-tag>
              <n-button text size="tiny" type="primary" @click="$router.push('/materials/upload')">
                <template #icon><n-icon :size="16"><add-outline /></n-icon></template>
              </n-button>
            </n-space>
          </template>
          <n-data-table v-if="materials.length" :columns="materialColumns" :data="materials"
            :row-key="(row) => row.id" size="small" striped :max-height="300" virtual-scroll />
          <n-empty v-else description="暂无材料" style="padding: 24px 0;">
            <template #extra>
              <n-button size="small" type="primary" @click="$router.push('/materials/upload')">上传材料</n-button>
            </template>
          </n-empty>
        </n-card>

        <n-card title="试卷格式模板" size="small" style="margin-top:12px;">
          <template #header-extra>
            <n-tag v-if="templateLoaded" type="success" size="small">已导入</n-tag>
          </template>
          <div v-if="!templateLoaded">
            <p style="font-size:13px;color:#6b7280;margin-bottom:8px;">导入一份已有试卷 (.docx/.pdf)，AI 将学习其排版格式</p>
            <n-upload accept=".docx,.pdf" :max="1" @change="handleTemplate" :show-file-list="false">
              <n-button size="small" type="primary" ghost>
                <template #icon><n-icon :size="16"><cloud-upload-outline /></n-icon></template>
                导入样卷
              </n-button>
            </n-upload>
          </div>
          <div v-else>
            <n-text style="font-size:13px;">✅ 已加载：<strong>{{ templateName }}</strong></n-text>
            <n-button size="tiny" text type="error" @click="clearTemplate" style="margin-left:8px;">清除</n-button>
            <p style="font-size:12px;color:#9ca3af;margin-top:4px;">组卷时将自动参考该样卷的排版格式</p>
          </div>
        </n-card>
      </n-grid-item>

      <n-grid-item>
        <n-card title="出卷助手" size="small">
          <template #header-extra>
            <n-tag type="primary" size="small">AI 对话</n-tag>
          </template>
          <ChatDialog @generate="handleGenerate" />
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- 下半部分：历史试卷 -->
    <n-card title="历史试卷" size="small">
      <template #header-extra>
        <n-tag type="success" size="small">{{ exams.length }} 份</n-tag>
      </template>
      <n-data-table v-if="exams.length" :columns="examColumns" :data="exams"
        :row-key="(row) => row.id" size="small" striped :max-height="360" virtual-scroll />
      <n-empty v-else description="暂无试卷" style="padding: 32px 0;" />
    </n-card>
  </div>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NTag, useMessage } from 'naive-ui'
import { CloudUploadOutline, AddOutline } from '@vicons/ionicons5'
import { materialApi } from '../../api/materials.js'
import { examApi } from '../../api/exams.js'
import { getQuestions } from '../../api/questions.js'
import ChatDialog from '../../components/ChatDialog.vue'

const router = useRouter()
const message = useMessage()
const materials = ref([])
const exams = ref([])
const questionTotal = ref(0)
const templateLoaded = ref(false)
const templateName = ref('')

const hour = new Date().getHours()
const greeting = hour < 6 ? '夜深了' : hour < 12 ? '上午好' : hour < 18 ? '下午好' : '晚上好'

function handleTemplate({ file }) {
  if (!file.file) return
  templateName.value = file.file.name
  templateLoaded.value = true
  localStorage.setItem('exam_template', JSON.stringify({ name: file.file.name, uploadedAt: Date.now() }))
  message.success('样卷已导入！组卷时将自动参考其格式')
}

function clearTemplate() {
  localStorage.removeItem('exam_template')
  templateLoaded.value = false
  templateName.value = ''
  message.info('样卷已清除')
}

function handleGenerate(requirements) {
  const params = new URLSearchParams()
  if (requirements.title) params.set('title', requirements.title)
  if (requirements.duration) params.set('duration', requirements.duration)
  if (requirements.total_score) params.set('totalScore', requirements.total_score)
  if (requirements.focus_notes) params.set('focusNotes', requirements.focus_notes)
  if (requirements.question_distribution) params.set('distribution', JSON.stringify(requirements.question_distribution))
  if (requirements.difficulty_distribution) params.set('difficulty', JSON.stringify(requirements.difficulty_distribution))
  router.push(`/exams/create?${params.toString()}`)
}

const materialColumns = [
  { title: '文件名', key: 'filename', ellipsis: { tooltip: true } },
  { title: '类型', key: 'file_type', width: 80 },
  { title: '上传时间', key: 'uploaded_at', width: 140, render: (row) => row.uploaded_at?.slice(0, 10) },
  {
    title: '操作', key: 'actions', width: 150,
    render: (row) => h('div', [
      h(NButton, { size: 'tiny', quaternary: true, onClick: () => router.push(`/knowledge/${row.id}`) }, { default: () => '知识树' }),
      h(NButton, { size: 'tiny', quaternary: true, onClick: () => router.push(`/materials/${row.id}`) }, { default: () => '详情' }),
    ]),
  },
]

const examColumns = [
  { title: '试卷名称', key: 'title' },
  { title: '状态', key: 'status', width: 80 },
  { title: '总分', key: 'total_score', width: 70 },
  { title: '时长', key: 'duration', width: 70, render: (row) => `${row.duration}min` },
  { title: '创建时间', key: 'created_at', width: 140, render: (row) => row.created_at?.slice(0, 10) },
  {
    title: '操作', key: 'actions', width: 100,
    render: (row) => h('div', [
      h(NButton, { size: 'tiny', quaternary: true, onClick: () => router.push(`/exams/${row.id}`) }, { default: () => '预览' }),
    ]),
  },
]

onMounted(async () => {
  const tmpl = localStorage.getItem('exam_template')
  if (tmpl) {
    try {
      const t = JSON.parse(tmpl)
      templateLoaded.value = true
      templateName.value = t.name || '未知文件'
    } catch {}
  }
  try {
    const [matRes, examRes, qRes] = await Promise.all([
      materialApi.list(),
      examApi.list(),
      getQuestions({ page: 1, page_size: 1 }),
    ])
    materials.value = matRes.data
    exams.value = examRes.data
    questionTotal.value = qRes.data.total || 0
  } catch (e) { message.error('加载数据失败') }
})
</script>

<style scoped>
.dash-hero {
  margin: 8px 0 28px;
}

.dash-title {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 0.3px;
  color: var(--ink);
}

.dash-sub {
  margin: 8px 0 20px;
  font-size: 14px;
  color: var(--text-3);
}

.dash-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.stat-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 18px 20px;
  background: #fff;
}

.stat-card b {
  font-size: 26px;
  font-weight: 700;
  color: var(--ink);
}

.stat-card span {
  display: block;
  color: var(--text-3);
  font-size: 13px;
  margin-top: 2px;
}

@media (max-width: 768px) {
  .dash-stats {
    grid-template-columns: 1fr;
  }
}
</style>
