<template>
  <div class="exam-review">
    <n-space align="center" style="margin-bottom: 8px;">
      <n-button text @click="$router.push('/dashboard')">
        <template #icon><n-icon><arrow-back-outline /></n-icon></template>
        返回首页
      </n-button>
      <n-divider vertical />
      <n-button text @click="$router.push('/exams')">
        <template #icon><n-icon><list-outline /></n-icon></template>
        试卷列表
      </n-button>
    </n-space>
    <n-h2 style="margin-bottom: 16px;">试卷确认与导出</n-h2>

    <n-card v-if="exam" size="small" style="margin-bottom: 12px;">
      <n-space align="center">
        <n-tag type="primary">{{ exam.title }}</n-tag>
        <n-text depth="3">总分: {{ exam.total_score }}分 | 时长: {{ exam.duration }}分钟 | {{ exam.questions?.length || 0 }}题</n-text>
        <n-button size="tiny" type="warning" @click="exportAnswerSheet" :loading="sheetLoading">📝 答题卡</n-button>
        <n-button v-if="verifyResult" size="tiny" :type="verifyResult.passed ? 'success' : 'error'" @click="activeTab = 'verify'">
          {{ verifyResult.passed ? '✓ 审核通过' : '✗ 审核未通过' }}
        </n-button>
      </n-space>
    </n-card>

    <n-card size="small">
      <n-tabs v-model:value="activeTab" type="line" animated>
        <!-- Tab 1: 试卷 -->
        <n-tab-pane name="exam" tab="试卷">
          <div class="content-panel">
            <pre class="exam-text">{{ examText }}</pre>
          </div>
          <div class="export-bar">
            <n-text depth="3" style="font-size:13px;">导出试卷:</n-text>
            <n-button size="small" @click="exportFile('exam', 'txt')">TXT</n-button>
            <n-button size="small" @click="exportFile('exam', 'pdf')">PDF</n-button>
            <n-button size="small" @click="exportFile('exam', 'docx')" type="primary">Word</n-button>
            <n-button size="small" type="warning" @click="exportAnswerSheet" :loading="sheetLoading">📝 答题卡</n-button>
          </div>
        </n-tab-pane>

        <!-- Tab 2: 答案与解析 -->
        <n-tab-pane name="answers" tab="答案与解析">
          <div class="content-panel">
            <pre class="exam-text">{{ answersText }}</pre>
          </div>
          <div class="export-bar">
            <n-text depth="3" style="font-size:13px;">导出答案:</n-text>
            <n-button size="small" @click="exportFile('answers', 'txt')">TXT</n-button>
            <n-button size="small" @click="exportFile('answers', 'pdf')">PDF</n-button>
            <n-button size="small" @click="exportFile('answers', 'docx')" type="primary">Word</n-button>
          </div>
        </n-tab-pane>

        <!-- Tab 4: PDF 预览 -->
        <n-tab-pane name="pdf" tab="PDF 预览">
          <div v-if="pdfLoading" style="text-align:center;padding:60px 0;">
            <n-spin size="large" />
            <p style="margin-top:12px;color:#6b7280;">正在生成 PDF 预览...</p>
          </div>
          <div v-else-if="pdfUrl" class="pdf-preview-container">
            <iframe :src="pdfUrl" class="pdf-iframe" frameborder="0" />
          </div>
          <div v-else style="text-align:center;padding:40px;color:#6b7280;">
            PDF 预览加载失败，请尝试导出下载
          </div>
          <div class="export-bar" v-if="pdfUrl">
            <n-text depth="3" style="font-size:13px;">导出试卷:</n-text>
            <n-button size="small" @click="exportFile('exam', 'txt')">TXT</n-button>
            <n-button size="small" @click="exportFile('exam', 'pdf')">PDF</n-button>
            <n-button size="small" @click="exportFile('exam', 'docx')" type="primary">Word</n-button>
          </div>
        </n-tab-pane>

        <!-- Tab 5: 审核结果 -->
        <n-tab-pane name="verify" tab="审核结果">
          <div v-if="!verifyResult && verifyLoading" style="text-align:center;padding:60px 0;">
            <n-spin size="large" />
            <p style="margin-top:12px;color:#6b7280;">正在审核试卷...</p>
          </div>
          <div v-else-if="verifyResult" class="content-panel">
            <div :style="{ textAlign: 'center', padding: '16px 0' }">
              <n-icon :size="48" :color="verifyResult.passed ? '#10B981' : '#EF4444'">
                <checkmark-circle-outline v-if="verifyResult.passed" />
                <close-circle-outline v-else />
              </n-icon>
              <h3 :style="{ color: verifyResult.passed ? '#10B981' : '#EF4444', margin: '8px 0' }">
                {{ verifyResult.passed ? '审核通过 ✓' : '审核未通过 ✗' }}
              </h3>
              <n-tag v-if="verifyResult.auto_fixed" type="warning" size="small">已自动修复</n-tag>
            </div>
            <n-divider />
            <div v-for="check in verifyResult.checks" :key="check.item" style="padding:8px 0;">
              <n-space align="center">
                <n-icon :size="18" :color="check.passed ? '#10B981' : '#EF4444'">
                  <checkmark-outline v-if="check.passed" />
                  <close-outline v-else />
                </n-icon>
                <n-text strong>{{ check.item }}</n-text>
                <n-tag :type="check.passed ? 'success' : 'error'" size="small">{{ check.passed ? '通过' : '未通过' }}</n-tag>
              </n-space>
              <p style="font-size:13px;color:#6b7280;margin:4px 0 0 26px;">{{ check.detail }}</p>
            </div>
            <div v-if="verifyResult.fix_log?.length" style="margin-top:12px;padding:12px;background:#ECFDF5;border-radius:6px;">
              <n-text depth="2" style="font-size:13px;">
                <strong>自动修复记录：</strong>{{ verifyResult.fix_log.join('；') }}
              </n-text>
            </div>
            <div style="margin-top:12px;text-align:center;">
              <n-button size="small" @click="loadVerify(); loadExam()" :loading="verifyLoading">重新审核</n-button>
            </div>
          </div>
          <div v-else class="content-panel" style="text-align:center;padding:40px;color:#6b7280;">
            审核结果不可用
          </div>
        </n-tab-pane>
      </n-tabs>
    </n-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { ArrowBackOutline, ListOutline, CheckmarkCircleOutline, CloseCircleOutline, CheckmarkOutline, CloseOutline } from '@vicons/ionicons5'
import { examApi } from '../../api/exams.js'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const activeTab = ref('exam')
const exam = ref(null)
const evaluation = ref(null)
const evaluating = ref(false)
const pdfUrl = ref(null)
const pdfLoading = ref(false)
const verifyResult = ref(null)
const verifyLoading = ref(false)
const sheetLoading = ref(false)

const TYPE_LABELS = { choice: '选择题', fill: '填空题', tf: '判断题', short_answer: '简答题', code: '算法设计题' }

const examText = computed(() => buildText(false))
const answersText = computed(() => buildText(true))

function buildText(withAnswer) {
  if (!exam.value) return ''
  const lines = [exam.value.title, '='.repeat(40), `总分: ${exam.value.total_score}分 | 考试时间: ${exam.value.duration}分钟`, '']
  const qs = exam.value.questions || []
  const order = ['choice', 'fill', 'tf', 'short_answer', 'code']
  const secNames = ['一', '二', '三', '四', '五']
  let n = 1, si = 0
  for (const t of order) {
    const g = qs.filter(q => q.type === t)
    if (!g.length) continue
    lines.push(`${secNames[si]}、${TYPE_LABELS[t] || t}`)
    lines.push('-'.repeat(30)); si++
    for (const q of g) {
      lines.push(`${n}. (${q.score}分) ${q.content}`)
      if (t === 'choice' && q.options) {
        const opts = Array.isArray(q.options)
          ? q.options
          : Object.keys(q.options).sort().map(k => `${k}. ${q.options[k]}`)
        opts.forEach(o => lines.push(`    ${o}`))
      }
      if (withAnswer) {
        lines.push(`    【答案】${q.answer || ''}`)
        if (q.explanation) lines.push(`    【解析】${q.explanation}`)
      }
      lines.push(''); n++
    }
  }
  return lines.join('\n')
}

async function loadExam() {
  try {
    const res = await examApi.get(route.params.id)
    exam.value = res.data
  } catch (e) { message.error('加载失败') }
}

async function loadEvaluation() {
  evaluating.value = true
  try {
    const res = await examApi.evaluate(route.params.id)
    evaluation.value = res.data
  } catch (e) {
    evaluation.value = null
    message.error('AI 评价失败: ' + (e.response?.data?.detail || e.message))
  } finally { evaluating.value = false }
}

async function loadPdfPreview() {
  pdfLoading.value = true
  try {
    const res = await examApi.exportExam(route.params.id, { format: 'pdf', withAnswer: false })
    // Revoke old URL if any
    if (pdfUrl.value) URL.revokeObjectURL(pdfUrl.value)
    pdfUrl.value = URL.createObjectURL(res.data)
  } catch (e) {
    pdfUrl.value = null
  } finally { pdfLoading.value = false }
}

async function loadVerify() {
  verifyLoading.value = true
  try {
    const res = await examApi.verify(route.params.id, true)
    verifyResult.value = res.data
  } catch (e) {
    verifyResult.value = null
  } finally { verifyLoading.value = false }
}

async function exportFile(type, format) {
  try {
    const withAnswer = type === 'answers'
    const res = await examApi.exportExam(route.params.id, { withAnswer, format })
    downloadBlob(res.data, `${exam.value.title}_${type === 'answers' ? '答案' : '试卷'}.${format}`)
    message.success('导出成功')
  } catch (e) { message.error('导出失败') }
}

async function exportAnswerSheet() {
  sheetLoading.value = true
  try {
    const res = await examApi.answerSheet(route.params.id)
    downloadBlob(res.data, `${exam.value?.title}_答题卡.pdf`)
    message.success('答题卡导出成功')
  } catch (e) { message.error('答题卡导出失败') }
  finally { sheetLoading.value = false }
}

function exportEval(format) {
  if (!evaluation.value) return
  const text = [
    `试卷评价报告 — ${exam.value?.title || ''}`,
    '='.repeat(40), `总评分: ${evaluation.value.total_rating}/100`, '',
    evaluation.value.comment || '', '',
    '知识点覆盖:', evaluation.value.knowledge_coverage || '', '',
    '考察重点:', evaluation.value.focus_analysis || '', '',
    '题型分布:', evaluation.value.type_distribution_review || '', '',
    '建议:', evaluation.value.suggestions || '',
  ].join('\n')
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  if (format === 'txt') {
    downloadBlob(blob, `${exam.value?.title}_评价.txt`)
  } else {
    message.info('评价报告 PDF/Word 导出需后端支持，当前先下载 TXT 格式')
  }
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

onMounted(() => { loadExam(); loadEvaluation(); loadVerify() })

watch(activeTab, (tab) => {
  if (tab === 'pdf' && !pdfUrl.value && !pdfLoading.value) loadPdfPreview()
})
</script>

<style scoped>
.exam-review { max-width: 900px; margin: 0 auto; }
.content-panel { max-height: 500px; overflow-y: auto; background: #fafafa; border: 1px solid #e5e7eb; border-radius: 6px; padding: 20px 24px; }
.exam-text { font-family: Consolas, monospace; font-size: 14px; line-height: 1.7; white-space: pre-wrap; word-break: break-word; color: #374151; margin: 0; }
.export-bar { display: flex; align-items: center; gap: 8px; padding: 12px 0 0; border-top: 1px solid #f0f0f0; margin-top: 12px; }
.eval-score { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 16px 0; }
.eval-label { font-size: 14px; color: #6b7280; }
.eval-text { font-size: 14px; line-height: 1.7; color: #374151; padding: 16px 0 0; border-top: 1px solid #e5e7eb; }
.pdf-preview-container { width: 100%; height: 600px; background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; overflow: hidden; }
.pdf-iframe { width: 100%; height: 100%; border: none; }
</style>
