<template>
  <div class="exam-wizard">
    <n-space align="center" style="margin-bottom: 8px;">
      <n-button text @click="$router.push('/dashboard')">
        <template #icon><n-icon><arrow-back-outline /></n-icon></template>
        返回首页
      </n-button>
    </n-space>
    <n-h2 style="margin-bottom: 16px;">智能组卷</n-h2>

    <n-grid :cols="3" :x-gap="16">
      <!-- 左侧：试卷预览 (2/3) -->
      <n-grid-item :span="2">
        <n-card title="试卷预览" size="small" style="min-height: 500px;">
          <template #header-extra>
            <n-tag v-if="!generating && questions.length" type="info" size="small">
              {{ questions.length }} 题 | 总分 {{ totalScore }}
            </n-tag>
          </template>

          <!-- Generating: show progress -->
          <div v-if="generating" class="preview-progress">
            <n-spin size="large" />
            <h3 style="margin: 20px 0 8px; color: #0E7C86;">正在生成试卷...</h3>
            <div class="progress-steps-large">
              <div v-for="(step, i) in progressSteps" :key="i" class="progress-step-large"
                   :class="{ active: i === currentStep, done: i < currentStep }">
                <div class="step-indicator">
                  <n-icon :size="20" :color="i < currentStep ? '#10B981' : i === currentStep ? '#0E7C86' : '#d1d5db'">
                    <checkmark-circle-outline v-if="i < currentStep" />
                    <ellipse-outline v-else />
                  </n-icon>
                </div>
                <div class="step-info">
                  <span class="step-label">{{ step }}</span>
                  <span v-if="i === 0 && currentStep >= 0" class="step-desc">从题库中检索相关题目...</span>
                  <span v-if="i === 1 && currentStep >= 1" class="step-desc">AI 生成补充题目...</span>
                  <span v-if="i === 2 && currentStep >= 2" class="step-desc">LLM 智能筛选和编排...</span>
                  <span v-if="i === 3 && currentStep >= 3" class="step-desc">自动校验并修复差异...</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Has questions: show preview -->
          <div v-else-if="questions.length" class="preview-list">
            <template v-for="group in groupedQuestions" :key="group.type">
              <div class="type-header">{{ group.label }}</div>
              <div v-for="(q, idx) in group.questions" :key="q.eq_id" class="question-item">
                <div class="q-header">
                  <span class="q-num">{{ q.displayNum }}.</span>
                  <n-tag :type="getTypeColor(q.type)" size="tiny">{{ getTypeLabel(q.type) }}</n-tag>
                  <span class="q-score">{{ q.score }}分</span>
                  <n-space :size="4" class="q-actions">
                    <n-button text size="tiny" @click="moveUp(q)">
                      <template #icon><n-icon :size="14"><chevron-up-outline /></n-icon></template>
                    </n-button>
                    <n-button text size="tiny" @click="moveDown(q)">
                      <template #icon><n-icon :size="14"><chevron-down-outline /></n-icon></template>
                    </n-button>
                    <n-button text size="tiny" type="primary" @click="openEdit(q)">
                      <template #icon><n-icon :size="14"><create-outline /></n-icon></template>
                    </n-button>
                    <n-popconfirm @positive-click="regenerateQuestion(q)">
                      <template #trigger>
                        <n-button text size="tiny" type="warning">
                          <template #icon><n-icon :size="14"><refresh-outline /></n-icon></template>
                        </n-button>
                      </template>
                      重新生成这道题？（保持题型和分值不变）
                    </n-popconfirm>
                  </n-space>
                </div>
                <div class="q-content">{{ q.content }}</div>
                <div v-if="q.options" class="q-options">
                  <div v-for="(opt, oi) in q.options" :key="oi" class="q-option">
                    {{ typeof oi === 'string' ? `${oi}. ${opt}` : opt }}
                  </div>
                </div>
              </div>
            </template>
          </div>

          <!-- Empty state -->
          <n-empty v-else description="请在右侧填写信息后点击「生成预览试卷」" style="padding: 60px 0;" />
        </n-card>
      </n-grid-item>

      <!-- 右侧：组卷设置 (1/3) -->
      <n-grid-item :span="1">
        <n-card title="组卷设置" size="small">
          <n-form :model="form" label-placement="top" size="small">
            <n-form-item label="试卷名称">
              <n-input v-model:value="form.title" placeholder="如: 数据结构期中考试" />
            </n-form-item>
            <n-grid cols="2" :x-gap="8">
              <n-grid-item>
                <n-form-item label="时长(分钟)">
                  <n-input-number v-model:value="form.duration" :min="30" :max="180" />
                </n-form-item>
              </n-grid-item>
              <n-grid-item>
                <n-form-item label="总分">
                  <n-input-number v-model:value="form.total_score" :min="50" :max="200" />
                </n-form-item>
              </n-grid-item>
            </n-grid>

            <n-divider style="margin: 8px 0;">题型配比</n-divider>
            <n-grid cols="2" :x-gap="8">
              <n-grid-item v-for="t in types" :key="t.key">
                <n-form-item :label="t.label">
                  <n-input-number v-model:value="form.question_distribution[t.key]" :min="0" :max="50" size="small" />
                </n-form-item>
              </n-grid-item>
            </n-grid>

            <n-divider style="margin: 8px 0;">难度分布 (%)</n-divider>
            <div class="diff-bars">
              <div v-for="d in 5" :key="d" class="diff-bar-row">
                <span class="diff-label">{{ d }}★</span>
                <div style="flex:1;margin:0 8px;">
                  <n-slider v-model:value="form.difficulty_distribution[String(d)]" :min="0" :max="100" :step="5" />
                </div>
                <span class="diff-val">{{ form.difficulty_distribution[String(d)] }}%</span>
              </div>
            </div>
            <div class="diff-summary-bar">
              <div v-for="d in 5" :key="d" class="diff-segment"
                :style="{
                  width: form.difficulty_distribution[String(d)] + '%',
                  background: diffColors[d - 1],
                }"
                :title="`${d}星: ${form.difficulty_distribution[String(d)]}%`"
              />
            </div>

            <n-form-item label="重点方向" style="margin-top:8px;">
              <n-input v-model:value="form.focus_notes" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }"
                placeholder="如: 重点考查二叉树遍历和排序算法" />
            </n-form-item>

            <n-form-item label="已选知识点">
              <n-tag v-for="id in form.knowledge_node_ids" :key="id" closable @close="removeNode(id)" size="small" style="margin:2px;">
                节点 #{{ id }}
              </n-tag>
              <n-text v-if="!form.knowledge_node_ids.length" depth="3" style="font-size:12px;">从知识树页面选择</n-text>
            </n-form-item>

            <n-divider style="margin: 8px 0;">试卷格式设置</n-divider>
            <n-collapse>
              <n-collapse-item title="考生信息栏" name="info">
                <n-space vertical :size="6">
                  <n-space align="center" justify="space-between">
                    <span style="font-size:13px;">显示"班级"字段</span>
                    <n-switch v-model:value="examFormat.showClass" size="small" />
                  </n-space>
                  <n-space align="center" justify="space-between">
                    <span style="font-size:13px;">显示"姓名"字段</span>
                    <n-switch v-model:value="examFormat.showName" size="small" />
                  </n-space>
                  <n-space align="center" justify="space-between">
                    <span style="font-size:13px;">显示"学号"字段</span>
                    <n-switch v-model:value="examFormat.showStudentId" size="small" />
                  </n-space>
                  <n-space align="center" justify="space-between">
                    <span style="font-size:13px;">显示"得分"栏</span>
                    <n-switch v-model:value="examFormat.showScore" size="small" />
                  </n-space>
                </n-space>
              </n-collapse-item>
              <n-collapse-item title="试卷头信息" name="header">
                <n-space vertical :size="6">
                  <n-space align="center" justify="space-between">
                    <span style="font-size:13px;">显示考试科目</span>
                    <n-switch v-model:value="examFormat.showSubject" size="small" />
                  </n-space>
                  <n-space align="center" justify="space-between">
                    <span style="font-size:13px;">显示考试时间</span>
                    <n-switch v-model:value="examFormat.showExamTime" size="small" />
                  </n-space>
                  <n-space align="center" justify="space-between">
                    <span style="font-size:13px;">显示分值说明</span>
                    <n-switch v-model:value="examFormat.showIntro" size="small" />
                  </n-space>
                  <n-form-item label="自定义标题（留空用试卷名）" style="margin-top:4px;">
                    <n-input v-model:value="examFormat.customTitle" size="small" placeholder="如: XX大学数据结构期末考试" />
                  </n-form-item>
                </n-space>
              </n-collapse-item>
            </n-collapse>
            <div v-if="examFormat.templateName" class="notify-text">
              📋 已参考样卷格式：{{ examFormat.templateName }}
            </div>
          </n-form>

          <n-divider />
          <n-space vertical :size="8">
            <n-button type="primary" @click="generate" block :disabled="!form.title">
              <template #icon><n-icon><play-outline /></n-icon></template>
              生成预览试卷
            </n-button>
            <n-button v-if="examId" type="success" @click="$router.push(`/exams/${examId}/review`)" block>
              ✓ 生成完整试卷
            </n-button>
          </n-space>

          <!-- 二次审核结果 (only shown when auto-fixed or passing) -->
          <div v-if="examId && verifyResult" style="margin-top: 12px;">
            <n-divider style="margin: 8px 0;" />
            <div v-if="verifyResult.passed" style="text-align:center;">
              <n-icon :size="20" color="#10B981" style="vertical-align:middle;">
                <checkmark-circle-outline />
              </n-icon>
              <n-text strong style="color:#10B981;margin-left:4px;">审核通过</n-text>
              <n-text v-if="verifyResult.auto_fixed" depth="3" style="font-size:11px;display:block;margin-top:4px;">
                已自动修复：{{ verifyResult.fix_log?.join('；') }}
              </n-text>
            </div>
            <n-text v-else depth="3" style="font-size:12px;">
              {{ verifyResult.fix_log?.join('；') || '正在自动修复...' }}
            </n-text>
          </div>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- 编辑题目弹窗 -->
    <n-modal v-model:show="editModal.show" title="编辑题目" preset="card" style="width:600px;">
      <n-form :model="editModal.form" label-placement="left" label-width="80" size="small">
        <n-form-item label="题型">
          <n-select v-model:value="editModal.form.type" :options="typeOptions" />
        </n-form-item>
        <n-form-item label="分值">
          <n-input-number v-model:value="editModal.form.score" :min="1" :max="100" />
        </n-form-item>
        <n-form-item label="题干">
          <n-input v-model:value="editModal.form.content" type="textarea" :autosize="{ minRows: 2, maxRows: 6 }" />
        </n-form-item>
        <n-form-item v-if="editModal.form.type === 'choice'" label="选项(每行一个)">
          <n-input v-model:value="editModal.form.optionsText" type="textarea"
            :autosize="{ minRows: 3, maxRows: 6 }" placeholder="A. 选项A&#10;B. 选项B" />
        </n-form-item>
        <n-form-item label="答案">
          <n-input v-model:value="editModal.form.answer" placeholder="正确答案" />
        </n-form-item>
        <n-form-item label="解析">
          <n-input v-model:value="editModal.form.explanation" type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }" placeholder="题目解析（可选）" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="editModal.show = false">取消</n-button>
          <n-button type="primary" @click="saveEdit" :loading="editModal.saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  CreateOutline, PlayOutline, ChevronUpOutline, ChevronDownOutline,
  RefreshOutline, ArrowBackOutline, CheckmarkCircleOutline,
  EllipseOutline,
} from '@vicons/ionicons5'
import { examApi } from '../../api/exams.js'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const types = [
  { key: 'choice', label: '选择题' }, { key: 'fill', label: '填空题' },
  { key: 'tf', label: '判断题' }, { key: 'short_answer', label: '简答题' },
  { key: 'code', label: '算法设计题' },
]
const typeOptions = types.map(t => ({ label: t.label, value: t.key }))

const TYPE_LABELS = { choice: '选择题', fill: '填空题', tf: '判断题', short_answer: '简答题', code: '算法设计题' }
const TYPE_COLORS = { choice: 'primary', fill: 'info', tf: 'warning', short_answer: 'success', code: 'error' }
const diffColors = ['#10B981', '#34D399', '#FBBF24', '#F97316', '#EF4444']
function getTypeLabel(t) { return TYPE_LABELS[t] || t }
function getTypeColor(t) { return TYPE_COLORS[t] || 'default' }

const generating = ref(false)
const questions = ref([])
const examId = ref(null)
const verifyResult = ref(null)
const verifying = ref(false)
const progressSteps = ['检索题库', 'AI 生成题目', 'AI 组卷筛选', '校验与修复']
const currentStep = ref(0)

const form = ref({
  title: '', duration: 120, total_score: 100, knowledge_node_ids: [],
  question_distribution: { choice: 10, fill: 5, tf: 5, short_answer: 3, code: 2 },
  difficulty_distribution: { '1': 10, '2': 30, '3': 30, '4': 20, '5': 10 },
  focus_notes: '',
})

const examFormat = ref({
  showClass: true, showName: true, showStudentId: true, showScore: true,
  showSubject: true, showExamTime: true, showIntro: true,
  customTitle: '', templateName: '',
})

onMounted(() => {
  if (route.query.title) form.value.title = route.query.title
  if (route.query.duration) form.value.duration = Number(route.query.duration)
  if (route.query.totalScore) form.value.total_score = Number(route.query.totalScore)
  if (route.query.focusNotes) form.value.focus_notes = route.query.focusNotes
  try { if (route.query.distribution) Object.assign(form.value.question_distribution, JSON.parse(route.query.distribution)) } catch {}
  try { if (route.query.difficulty) Object.assign(form.value.difficulty_distribution, JSON.parse(route.query.difficulty)) } catch {}
  const ids = route.query.nodeIds
  if (ids) form.value.knowledge_node_ids = ids.split(',').map(Number)
  // 读取样卷
  const tmpl = localStorage.getItem('exam_template')
  if (tmpl) {
    try {
      const t = JSON.parse(tmpl)
      examFormat.value.templateName = t.name || ''
      if (t.format) Object.assign(examFormat.value, t.format)
    } catch {}
  }
})

const totalScore = computed(() => questions.value.reduce((s, q) => s + q.score, 0))

const groupedQuestions = computed(() => {
  const order = ['choice', 'fill', 'tf', 'short_answer', 'code']
  const groups = []; let n = 1
  for (const t of order) {
    const qs = questions.value.filter(q => q.type === t)
    if (qs.length) groups.push({ type: t, label: TYPE_LABELS[t], questions: qs.map(q => ({ ...q, displayNum: n++ })) })
  }
  return groups
})

const editModal = ref({ show: false, saving: false, editingQ: null, form: { type: '', score: 0, content: '', optionsText: '' } })

function removeNode(id) { form.value.knowledge_node_ids = form.value.knowledge_node_ids.filter(n => n !== id) }

async function generate() {
  generating.value = true
  verifyResult.value = null
  currentStep.value = 0

  // Animate progress steps
  const stepTimer = setInterval(() => {
    if (currentStep.value < 3) currentStep.value++
  }, 2000)

  try {
    currentStep.value = 1  // 检索题库 + AI 生成
    const payload = { ...form.value, format: examFormat.value }
    const res = await examApi.generate(payload)
    examId.value = res.data.exam_id
    currentStep.value = 2  // AI 组卷筛选完成

    await loadQuestions()
    currentStep.value = 3  // 开始校验与修复

    // Auto-verify with auto-fix
    const vRes = await examApi.verify(examId.value, true)
    verifyResult.value = vRes.data

    if (vRes.data.passed) {
      if (vRes.data.auto_fixed) {
        message.success('生成完成，已自动修复并校准')
        await loadQuestions() // reload after fix
      } else {
        message.success(`生成成功！共 ${res.data.question_count} 道题`)
      }
    } else {
      // Still failed after auto-fix — this shouldn't happen but handle gracefully
      message.warning('生成完成，部分项目需要手动调整')
    }
    currentStep.value = 4
  } catch (e) {
    message.error('生成失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    clearInterval(stepTimer)
    generating.value = false
  }
}

async function loadQuestions() {
  if (!examId.value) return
  try {
    const res = await examApi.get(examId.value)
    questions.value = res.data.questions || []
  } catch (e) { message.error('加载题目失败') }
}

async function regenerateQuestion(q) {
  try {
    await examApi.regenerateQuestion(examId.value, q.eq_id)
    message.success('题目已重新生成')
    await loadQuestions()
  } catch (e) { message.error('重新生成失败') }
}

function openEdit(q) {
  editModal.value = { show: true, saving: false, editingQ: q,
    form: {
      type: q.type, score: q.score, content: q.content,
      optionsText: q.options ? (Array.isArray(q.options) ? q.options.join('\n') : Object.keys(q.options).sort().map(k => `${k}. ${q.options[k]}`).join('\n')) : '',
      answer: q.answer || '', explanation: q.explanation || '',
    } }
}

async function saveEdit() {
  const q = editModal.value.editingQ; if (!q) return
  editModal.value.saving = true
  try {
    const f = editModal.value.form
    await examApi.replaceQuestion(examId.value, q.eq_id, {
      content: f.content, type: f.type, score: f.score,
      answer: f.answer, explanation: f.explanation,
      options: f.optionsText ? f.optionsText.split('\n').filter(Boolean) : null,
    })
    editModal.value.show = false; await loadQuestions(); message.success('已更新')
  } catch (e) { message.error('更新失败') }
  finally { editModal.value.saving = false }
}

async function moveUp(q) {
  const idx = questions.value.findIndex(x => x.eq_id === q.eq_id)
  if (idx <= 0) return
  const prev = questions.value[idx - 1]
  await examApi.replaceQuestion(examId.value, prev.eq_id, { sort_order: q.sort_order })
  await examApi.replaceQuestion(examId.value, q.eq_id, { sort_order: prev.sort_order })
  await loadQuestions()
}

async function moveDown(q) {
  const idx = questions.value.findIndex(x => x.eq_id === q.eq_id)
  if (idx >= questions.value.length - 1) return
  const next = questions.value[idx + 1]
  await examApi.replaceQuestion(examId.value, next.eq_id, { sort_order: q.sort_order })
  await examApi.replaceQuestion(examId.value, q.eq_id, { sort_order: next.sort_order })
  await loadQuestions()
}
</script>

<style scoped>
.exam-wizard { max-width: 1400px; margin: 0 auto; }
.preview-list { display: flex; flex-direction: column; gap: 2px; }
.type-header { font-size: 15px; font-weight: 600; color: #0E7C86; padding: 12px 0 4px; border-bottom: 2px solid #e5e7eb; margin-top: 4px; }
.question-item { padding: 10px 12px; border-radius: 6px; border: 1px solid #f0f0f0; background: #fafafa; transition: background .15s; }
.question-item:hover { background: #f0f0ff; }
.q-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.q-num { font-weight: 700; font-size: 14px; color: #0E7C86; min-width: 24px; }
.q-score { font-size: 12px; color: #9ca3af; margin-left: auto; }
.q-actions { margin-left: 4px; opacity: 0; transition: opacity .15s; }
.question-item:hover .q-actions { opacity: 1; }
.q-content { font-size: 14px; line-height: 1.6; color: #374151; padding-left: 32px; white-space: pre-wrap; }
.q-options { padding-left: 32px; margin-top: 4px; }
.q-option { font-size: 13px; color: #6b7280; line-height: 1.6; }

/* Difficulty bars */
.diff-bars { display: flex; flex-direction: column; gap: 2px; }
.diff-bar-row { display: flex; align-items: center; }
.diff-label { font-size: 12px; width: 24px; text-align: center; color: #6b7280; }
.diff-val { font-size: 12px; width: 32px; text-align: right; color: #6b7280; }
.diff-summary-bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 4px; background: #e5e7eb; }
.diff-segment { transition: width .3s; }
.notify-text { margin-top: 8px; font-size: 12px; color: #0E7C86; background: #E9F4F5; padding: 6px 8px; border-radius: 4px; }
.verify-check { display: flex; align-items: flex-start; padding: 2px 0; color: #4b5563; }
.preview-progress { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 400px; padding: 40px 20px; }
.preview-progress h3 { font-size: 18px; }
.progress-steps-large { width: 100%; max-width: 420px; margin-top: 16px; display: flex; flex-direction: column; gap: 16px; }
.progress-step-large { display: flex; align-items: flex-start; gap: 12px; padding: 12px 16px; border-radius: 8px; background: #f9fafb; transition: all .3s; }
.progress-step-large.active { background: #E9F4F5; box-shadow: 0 0 0 2px #0E7C8620; }
.progress-step-large.done { background: #ECFDF5; }
.step-indicator { flex-shrink: 0; padding-top: 1px; }
.step-info { display: flex; flex-direction: column; }
.step-label { font-size: 14px; font-weight: 500; color: #d1d5db; transition: color .3s; }
.progress-step-large.active .step-label { color: #0E7C86; font-weight: 600; }
.progress-step-large.done .step-label { color: #10B981; }
.step-desc { font-size: 12px; color: #9ca3af; margin-top: 2px; }
</style>
