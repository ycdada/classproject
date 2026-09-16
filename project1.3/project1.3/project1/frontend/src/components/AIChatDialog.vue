<template>
  <div class="ai-chat-wrapper">
    <!-- Floating button (collapsed) -->
    <n-button
      v-if="!isOpen"
      class="ai-fab"
      circle
      size="large"
      type="primary"
      @click="open"
    >
      <template #icon>🤖</template>
    </n-button>

    <!-- Chat panel (expanded) -->
    <n-card
      v-else
      :class="['ai-panel', { 'ai-panel--fullscreen': isFullscreen }]"
      :bordered="true"
    >
      <template #header>
        <div class="ai-panel__header">
          <span>🤖 AI 助教</span>
          <n-space>
            <n-button size="tiny" @click="toggleFullscreen">
              {{ isFullscreen ? '⊠' : '⛶' }}
            </n-button>
            <n-button size="tiny" @click="close">✕</n-button>
          </n-space>
        </div>
      </template>

      <div class="ai-panel__body" ref="msgContainer">
        <div v-for="(msg, i) in messages" :key="i" class="ai-msg" :class="'ai-msg--' + msg.role">
          <template v-if="msg.role === 'assistant' && msg.toolResult">
            <component
              :is="getToolCard(msg.toolResult.name)"
              :data="msg.toolResult.result"
              @add-to-exam="handleAddToExam"
              @preview-exam="handlePreviewExam"
            />
            <!-- Jump to exam button after generate_exam -->
            <div v-if="msg.toolResult.name === 'generate_exam' && msg.toolResult.result?.exam_id" class="ai-jump-btn">
              <n-button type="primary" size="small" @click="jumpToExam(msg.toolResult.result.exam_id)">
                查看试卷
              </n-button>
            </div>
          </template>
          <div v-else class="ai-msg__text" v-html="renderMd(msg.content)"></div>
        </div>
        <!-- Typing indicator -->
        <div v-if="isTyping" class="ai-msg ai-msg--assistant">
          <span class="ai-typing-cursor">|</span>
        </div>
      </div>

      <div class="ai-panel__footer">
        <n-space class="ai-quick-btns">
          <n-button size="tiny" @click="quickAction('帮我搜题：二叉树')">🔍 查题</n-button>
          <n-button size="tiny" @click="quickAction('帮我出一份试卷，范围是第1-3章')">🎯 组卷</n-button>
          <n-button size="tiny" @click="quickAction('解释一下二叉树的遍历方式')">📖 问答</n-button>
        </n-space>
        <n-input
          v-model:value="input"
          type="textarea"
          placeholder="描述你的需求..."
          :autosize="{ minRows: 1, maxRows: 3 }"
          @keydown.enter.exact.prevent="send"
        />
        <n-button type="primary" size="small" @click="send" :loading="isTyping">
          发送
        </n-button>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, nextTick, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { useSSE } from '../composables/useSSE.js'
import { renderMarkdown } from '../utils/markdown.js'
import QuestionSearchCard from './QuestionSearchCard.vue'
import ExamSummaryCard from './ExamSummaryCard.vue'

const router = useRouter()
const { sendMessage, cancel } = useSSE()

const isOpen = ref(false)
const isFullscreen = ref(false)
const isTyping = ref(false)
const input = ref('')
const messages = shallowRef([])
const msgContainer = ref(null)

const toolCardMap = {
  search_questions: QuestionSearchCard,
  generate_exam: ExamSummaryCard,
}

function getToolCard(toolName) {
  return toolCardMap[toolName] || 'div'
}

function renderMd(text) {
  return renderMarkdown(text)
}

function open() {
  isOpen.value = true
}

function close() {
  isOpen.value = false
  isFullscreen.value = false
}

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
}

async function send() {
  const text = input.value.trim()
  if (!text || isTyping.value) return

  input.value = ''
  messages.value = [...messages.value, { role: 'user', content: text }]
  const assistantMsg = { role: 'assistant', content: '', toolResult: null }
  messages.value = [...messages.value, assistantMsg]

  isTyping.value = true
  const history = messages.value
    .filter(m => m.role === 'user' || (m.role === 'assistant' && !m.toolResult))
    .map(m => ({ role: m.role, content: m.content }))
    .slice(0, -1)

  await sendMessage(text, history, {
    onText(chunk) {
      assistantMsg.content += chunk
      messages.value = [...messages.value]
      scrollToBottom()
    },
    onToolCall(data) {
      assistantMsg.toolResult = data
      messages.value = [...messages.value]
    },
    onDone() {
      isTyping.value = false
      scrollToBottom()
    },
    onError(err) {
      assistantMsg.content = `**错误：**${err}`
      isTyping.value = false
      messages.value = [...messages.value]
    },
  })
}

function quickAction(prompt) {
  input.value = prompt
  send()
}

function handleAddToExam(questionId) {
  input.value = `把题目 #${questionId} 加入当前试卷`
  send()
}

function handlePreviewExam(examData) {
  if (examData?.exam_id) {
    router.push(`/exams/${examData.exam_id}`)
  } else if (examData?.id) {
    router.push(`/exams/${examData.id}`)
  }
}

function jumpToExam(examId) {
  router.push(`/exams/${examId}`)
}

function scrollToBottom() {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.ai-chat-wrapper {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
}

.ai-fab {
  width: 56px;
  height: 56px;
  font-size: 24px;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4);
  animation: breathe 2s ease-in-out infinite;
}

@keyframes breathe {
  0%, 100% { box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4); }
  50% { box-shadow: 0 4px 24px rgba(79, 70, 229, 0.7); }
}

.ai-panel {
  width: 400px;
  height: 600px;
  display: flex;
  flex-direction: column;
}

.ai-panel--fullscreen {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 900px;
  height: 700px;
  z-index: 2000;
}

.ai-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ai-panel__body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.ai-panel__footer {
  border-top: 1px solid #eee;
  padding-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-quick-btns {
  margin-bottom: 4px;
}

.ai-msg {
  margin-bottom: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  max-width: 85%;
  word-break: break-word;
}

.ai-msg--user {
  background: #0E7C86;
  color: white;
  margin-left: auto;
}

.ai-msg--assistant {
  background: #f3f4f6;
  color: #333;
}

.ai-msg__text {
  line-height: 1.6;
}

.ai-msg__text :deep(p) {
  margin: 4px 0;
}

.ai-msg__text :deep(strong) {
  font-weight: 600;
}

.ai-msg__text :deep(ul),
.ai-msg__text :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}

.ai-msg__text :deep(code) {
  background: rgba(0,0,0,0.06);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 0.9em;
}

.ai-msg__text :deep(pre) {
  background: rgba(0,0,0,0.06);
  padding: 8px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.85em;
}

.ai-jump-btn {
  margin-top: 8px;
}

.ai-typing-cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
