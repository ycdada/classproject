import api from './index.js'

export const chatApi = {
  async sendSSE(message, history, { onText, onToolCall, onDone, onError }) {
    const token = document.cookie
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message, history }),
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let currentEvent = ''
    let currentData = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            currentData = line.slice(6)
            if (currentEvent === 'text') {
              // 后端将 text 块 JSON 编码为单行，避免换行打碎 SSE 帧
              try {
                onText?.(JSON.parse(currentData))
              } catch {
                onText?.(currentData)
              }
            } else if (currentEvent === 'tool_call') {
              try {
                onToolCall?.(JSON.parse(currentData))
              } catch {}
            } else if (currentEvent === 'done') {
              onDone?.()
            } else if (currentEvent === 'error') {
              try {
                const err = JSON.parse(currentData)
                onError?.(new Error(err.message || '服务器错误'))
              } catch {
                onError?.(new Error(currentData || '未知错误'))
              }
            }
            currentEvent = ''
            currentData = ''
          }
        }
      }
    } catch (e) {
      onError?.(e)
    }
  },
}

import apiStatic from './index.js'

export const parseRequirementsApi = {
  parse(messages) {
    return apiStatic.post('/chat/parse-requirements', { messages })
  },
}
