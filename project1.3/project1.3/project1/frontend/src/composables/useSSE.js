/**
 * SSE composable — connect to /api/chat, parse event stream, handle reconnect.
 */
export function useSSE() {
  let abortController = null

  async function sendMessage(message, history, callbacks) {
    const { onText, onToolCall, onDone, onError } = callbacks
    abortController = new AbortController()

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history }),
        signal: abortController.signal,
      })

      if (!response.ok) {
        const errText = await response.text()
        onError && onError(`HTTP ${response.status}: ${errText}`)
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let eventType = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (eventType === 'text') {
              // 后端将 text 块 JSON 编码为单行，避免换行打碎 SSE 帧
              try {
                onText && onText(JSON.parse(data))
              } catch {
                onText && onText(data)
              }
            } else if (eventType === 'tool_call') {
              try {
                onToolCall && onToolCall(JSON.parse(data))
              } catch (e) {
                console.warn('Failed to parse tool_call data:', e)
              }
            } else if (eventType === 'done') {
              onDone && onDone()
            } else if (eventType === 'error') {
              try {
                const err = JSON.parse(data)
                onError && onError(err.message || '服务器错误')
              } catch (e) {
                onError && onError(data || '未知错误')
              }
            }
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        onError && onError(err.message || '连接失败')
      }
    }
  }

  function cancel() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
  }

  return { sendMessage, cancel }
}
