<template>
  <div class="chat-container">
    <div class="chat-messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="chat-welcome">
        <p style="margin-bottom:10px;">描述你的出卷需求，AI 帮你智能组卷</p>
        <n-space justify="center" :size="6">
          <n-tag v-for="tag in quickTags" :key="tag" type="info" size="small"
            @click="sendQuick(tag)" class="quick-tag">{{ tag }}</n-tag>
        </n-space>
      </div>
      <div v-for="(msg, idx) in messages" :key="idx" :class="['chat-msg', msg.role]">
        <div class="chat-bubble">
          <div v-html="renderMd(msg.content)"></div>
          <n-button v-if="msg.toolCall && msg.toolCall.name === 'generate_exam'"
            type="primary" size="small" ghost style="margin-top:8px"
            @click="handleApplyGenerate(msg.toolCall)">
            按此方案生成试卷
          </n-button>
        </div>
      </div>
      <div v-if="loading" class="chat-msg assistant">
        <div class="chat-bubble typing">
          <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
      </div>
    </div>
    <div class="chat-input">
      <n-input v-model:value="inputText" type="textarea"
        placeholder="输入出卷需求..." :autosize="{ minRows: 1, maxRows: 3 }"
        @keydown.enter.exact.prevent="handleSend" :disabled="loading" size="small" />
      <n-button type="primary" size="small" @click="handleSend" :loading="loading"
        :disabled="!inputText.trim()">
        <template #icon><n-icon :size="18"><send-outline /></n-icon></template>
      </n-button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { useMessage } from 'naive-ui'
import { SendOutline } from '@vicons/ionicons5'
import { chatApi } from '../api/chat.js'
import { renderMarkdown } from '../utils/markdown.js'

const emit = defineEmits(['generate'])
const message = useMessage()
const messagesRef = ref(null)
const inputText = ref('')
const loading = ref(false)
const messages = ref([])
const textBuffer = ref('')

const quickTags = [
  '帮我出一份数据结构期中试卷',
  '二叉树章节单元测验',
  '排序与查找综合试题',
]

function renderMd(text) {
  return renderMarkdown(text)
}

function sendQuick(text) { inputText.value = text; handleSend() }

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true
  textBuffer.value = ''
  const assistantMsg = { role: 'assistant', content: '', toolCall: null }
  messages.value.push(assistantMsg)

  await nextTick(); scrollToBottom()

  await chatApi.sendSSE(text, messages.value.slice(0, -2).map(m => ({
    role: m.role,
    content: m.content,
  })), {
    onText(chunk) {
      textBuffer.value += chunk
      assistantMsg.content = textBuffer.value
    },
    onToolCall(toolCall) {
      assistantMsg.toolCall = toolCall
    },
    onDone() {
      loading.value = false
      scrollToBottom()
    },
    onError() {
      loading.value = false
      message.error('对话失败，请重试')
    },
  })
  scrollToBottom()
}

function handleApplyGenerate(toolCall) {
  const args = toolCall.arguments || {}
  const requirements = {
    title: args.title || '数据结构试卷',
    duration: args.duration || 120,
    total_score: args.total_score || 100,
    focus_notes: args.scope || '',
    question_distribution: {
      choice: args.choice_count || 10,
      fill: args.fill_count || 5,
      tf: args.tf_count || 5,
      short_answer: args.short_answer_count || 3,
      code: args.code_count || 2,
    },
    difficulty_distribution: { '1': 10, '2': 30, '3': 30, '4': 20, '5': 10 },
  }
  emit('generate', requirements)
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  })
}
</script>

<style scoped>
.chat-container { display: flex; flex-direction: column; height: 400px; overflow: hidden; }
.chat-messages {
  flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px;
  background: #f8f9fa; border-radius: 6px;
}
.chat-welcome { text-align: center; padding: 40px 16px; color: #6b7280; font-size: 13px; }
.quick-tag { cursor: pointer; }
.quick-tag:hover { opacity: 0.7; }
.chat-msg { display: flex; }
.chat-msg.user { justify-content: flex-end; }
.chat-msg.assistant { justify-content: flex-start; }
.chat-bubble {
  max-width: 85%; padding: 8px 12px; border-radius: 10px; font-size: 13px;
  line-height: 1.55; word-break: break-word;
}
.chat-bubble :deep(p) { margin: 4px 0; }
.chat-bubble :deep(strong) { font-weight: 600; }
.chat-bubble :deep(ul), .chat-bubble :deep(ol) { padding-left: 20px; margin: 4px 0; }
.chat-msg.user .chat-bubble { background: #0E7C86; color: #fff; border-radius: 10px 10px 4px 10px; }
.chat-msg.assistant .chat-bubble { background: #fff; color: #374151; border: 1px solid #e5e7eb; border-radius: 10px 10px 10px 4px; }
.chat-bubble.typing { display: flex; gap: 3px; padding: 12px 16px; }
.dot { width: 5px; height: 5px; border-radius: 50%; background: #9ca3af; animation: blink 1.4s infinite both; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%,80%,100%{opacity:.3} 40%{opacity:1} }
.chat-input { display: flex; gap: 6px; padding: 10px 0 0; align-items: flex-end; }
.chat-input :deep(.n-input) { flex: 1; }
</style>
