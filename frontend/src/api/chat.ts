import type { ExamDemand } from '../types'

// LangGraph SSE chat 客户端 — 只调 /api/chat
export type ChatEventName = 'intent' | 'tool_call' | 'scope_pending' | 'review_pending' | 'scope' | 'review' | 'text' | 'done' | 'error'

export interface ChatEventData {
  intent?: { next_action: string }
  tool_call?: { tool: string; result: unknown }
  scope_pending?: { scope_id: number; tree: unknown[]; message: string }
  review_pending?: { exam_paper: unknown; message: string }
  scope?: { status: string }
  review?: { status: string }
  text?: string
  error?: { message: string }
}

export interface ChatResume {
  kind: 'scope' | 'paper'
  confirmed?: boolean
  approved?: boolean
  adjustments?: string
  scope_id?: number
}

export interface ChatCallbacks {
  onEvent: (name: ChatEventName, data: ChatEventData) => void
  onError?: (err: unknown) => void
}

export async function streamChat(
  body: { message?: string; thread_id: string; resume?: ChatResume },
  cb: ChatCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  let res: Response
  try {
    res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    })
  } catch (err) {
    cb.onError?.(err)
    return
  }

  if (!res.ok || !res.body) {
    cb.onError?.(new Error(`chat HTTP ${res.status}`))
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const dispatch = (rawData: string, eventName: string) => {
    let data: unknown = rawData
    try {
      data = JSON.parse(rawData)
    } catch {
      /* keep as string */
    }
    cb.onEvent(eventName as ChatEventName, data as ChatEventData)
  }

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let idx: number
    while ((idx = buffer.indexOf('\n\n')) >= 0) {
      const frame = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      let eventName = 'message'
      const dataLines: string[] = []
      for (const line of frame.split('\n')) {
        if (line.startsWith('event: ')) eventName = line.slice(7).trim()
        else if (line.startsWith('data: ')) dataLines.push(line.slice(6))
      }
      if (dataLines.length) dispatch(dataLines.join('\n'), eventName)
    }
  }
}

export function makeThread(): string {
  return `t-${Date.now()}-${Math.floor(Math.random() * 1e6)}`
}

export type { ExamDemand }
