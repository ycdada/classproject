import { useEffect, useRef, useState } from 'react'
import { Button, Drawer, FloatButton, Input, List, Typography, message } from 'antd'
import { CommentOutlined, SendOutlined } from '@ant-design/icons'
import { makeThread, streamChat, type ChatEventData, type ChatEventName } from '../api/chat'
import { useNavigate } from 'react-router-dom'

interface ChatMsg {
  role: 'teacher' | 'assistant'
  content: string
  scopeId?: number
  reviewPending?: boolean
  streaming?: boolean
}

function dataOf(name: ChatEventName, data: ChatEventData): string | null {
  switch (name) {
    case 'text':
      return typeof data === 'string' ? data : (data.text ?? '')
    case 'error':
      return `[助手错误] ${data.error?.message ?? '未知错误'}`
    default:
      return null
  }
}

export default function ChatDock({ embedded = false }: { embedded?: boolean }) {
  const [open, setOpen] = useState(!embedded)
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const threadRef = useRef(makeThread())
  const bodyRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight
    }
  }, [messages, open])

  async function handleEvent(name: ChatEventName, data: ChatEventData) {
    if (name === 'scope_pending' && data.scope_pending) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: data.scope_pending!.message || '已提出考查范围，请确认', scopeId: data.scope_pending!.scope_id },
      ])
      return
    }
    if (name === 'review_pending') {
      setMessages((m) => [...m, { role: 'assistant', content: '试卷已装配，请在预览页调整。', reviewPending: true }])
      return
    }
    const text = dataOf(name, data)
    if (text) {
      setMessages((m) => {
        const last = m[m.length - 1]
        if (last && last.role === 'assistant' && last.streaming) {
          const copy = [...m]
          copy[copy.length - 1] = { ...last, content: last.content + text }
          return copy
        }
        return [...m, { role: 'assistant', content: text }]
      })
    }
  }

  async function send(text?: string) {
    const content = (text ?? input).trim()
    if (!content || busy) return
    setBusy(true)
    setInput('')
    setMessages((m) => [...m, { role: 'teacher', content }, { role: 'assistant', content: '', streaming: true } as ChatMsg])
    try {
      await streamChat({ message: content, thread_id: threadRef.current }, {
        onEvent: handleEvent,
        onError: (err) => message.error((err as Error).message || '连接教学助手失败'),
      })
    } finally {
      setBusy(false)
      setMessages((m) => {
        const copy = [...m]
        const last = copy[copy.length - 1]
        if (last && last.streaming) {
          if (!last.content) last.content = '（助手无回复）'
          delete last.streaming
        }
        return copy
      })
    }
  }

  const body = (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div ref={bodyRef} style={{ flex: 1, overflow: 'auto', padding: '12px 16px', minHeight: 300 }}>
        {messages.length === 0 && (
          <Typography.Text type="secondary">
            可以让我搜题、查知识，或描述组卷需求——组卷前我会先提出考查范围请你确认。
          </Typography.Text>
        )}
        <List
          dataSource={messages}
          renderItem={(m) => (
            <div style={{ textAlign: m.role === 'teacher' ? 'right' : 'left', margin: '8px 0' }}>
              {m.role === 'teacher' ? (
                <Typography.Text strong>{m.content}</Typography.Text>
              ) : (
                <div>
                  <Typography.Text>{m.content}</Typography.Text>
                  {m.scopeId && (
                    <div style={{ marginTop: 6 }}>
                      <Button
                        size="small"
                        type="primary"
                        onClick={() => navigate('/exams/create')}
                      >
                        去确认考查范围
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        />
      </div>
      <div style={{ borderTop: '1px solid #f0f0f0', padding: 12, display: 'flex', gap: 8 }}>
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={() => send()}
          placeholder="向教学助手提问…"
          disabled={busy}
        />
        <Button type="primary" icon={<SendOutlined />} loading={busy} onClick={() => send()} />
      </div>
    </div>
  )

  if (embedded) return body

  return (
    <>
      <FloatButton
        icon={<CommentOutlined />}
        type="primary"
        tooltip="教学助手"
        style={{ right: 24, bottom: 24 }}
        onClick={() => setOpen(true)}
      />
      <Drawer
        title="教学助手"
        placement="right"
        width={420}
        open={open}
        onClose={() => setOpen(false)}
        styles={{ body: { padding: 0 } }}
      >
        {body}
      </Drawer>
    </>
  )
}
