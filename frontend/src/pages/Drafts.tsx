import { useEffect, useState } from 'react'
import {
  Button,
  Card,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { QuestionDraft, QuestionType } from '../types'
import { acceptDraft, listDrafts, rejectDraft, updateDraft } from '../api/drafts'

const TYPE_OPTIONS: Array<{ value: QuestionType; label: string }> = [
  { value: 'choice', label: '选择题' },
  { value: 'fill', label: '填空题' },
  { value: 'tf', label: '判断题' },
  { value: 'short_answer', label: '简答题' },
  { value: 'code', label: '算法设计题' },
]

export default function Drafts() {
  const [items, setItems] = useState<QuestionDraft[]>([])
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState<QuestionDraft | null>(null)
  const [form, setForm] = useState({ content: '', answer: '', explanation: '', difficulty: 3, type: 'choice' as QuestionType })

  async function refresh() {
    setLoading(true)
    try {
      setItems(await listDrafts('pending'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  function openEdit(d: QuestionDraft) {
    setEditing(d)
    setForm({
      content: d.content,
      answer: d.answer,
      explanation: d.explanation ?? '',
      difficulty: d.difficulty,
      type: d.type,
    })
  }

  async function saveEdit() {
    if (!editing) return
    await updateDraft(editing.id, form)
    message.success('已保存')
    setEditing(null)
    await refresh()
  }

  async function accept(d: QuestionDraft) {
    await acceptDraft(d.id)
    message.success('已接受，题目进入题库')
    await refresh()
  }

  async function reject(d: QuestionDraft) {
    await rejectDraft(d.id)
    message.success('已拒绝')
    await refresh()
  }

  const columns: ColumnsType<QuestionDraft> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    {
      title: '题型',
      dataIndex: 'type',
      width: 90,
      render: (t: string) => TYPE_OPTIONS.find((o) => o.value === t)?.label ?? t,
    },
    { title: '难度', dataIndex: 'difficulty', width: 60 },
    { title: '题干', dataIndex: 'content', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (s: string) => <Tag color={s === 'pending' ? 'orange' : s === 'accepted' ? 'green' : 'red'}>{s}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_, record) => (
        <>
          <Button size="small" type="link" onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Button size="small" type="link" style={{ color: '#389e0d' }} onClick={() => accept(record)}>
            接受
          </Button>
          <Button size="small" type="link" danger onClick={() => reject(record)}>
            拒绝
          </Button>
        </>
      ),
    },
  ]

  return (
    <Card title="题目草稿（待审核）">
      <Typography.Paragraph type="secondary">
        草稿是组卷时因题库缺口拟出的候选题。接受后才会进入题库；未确认的草稿不会出现在试卷上。
      </Typography.Paragraph>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        columns={columns}
        pagination={{ pageSize: 10, showSizeChanger: false }}
        locale={{ emptyText: <Typography.Text type="secondary">没有待审核的草稿。</Typography.Text> }}
      />

      <Modal
        open={!!editing}
        title={`编辑草稿 #${editing?.id ?? ''}`}
        onCancel={() => setEditing(null)}
        onOk={saveEdit}
        width={560}
        destroyOnClose
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space>
            <Select
              value={form.type}
              style={{ width: 140 }}
              options={TYPE_OPTIONS}
              onChange={(t) => setForm({ ...form, type: t })}
            />
            <span>
              难度
              <InputNumber
                min={1}
                max={5}
                value={form.difficulty}
                onChange={(v) => setForm({ ...form, difficulty: v ?? 3 })}
                style={{ marginLeft: 6 }}
              />
            </span>
          </Space>
          <Input.TextArea
            rows={3}
            value={form.content}
            onChange={(e) => setForm({ ...form, content: e.target.value })}
            placeholder="题干"
          />
          <Input
            value={form.answer}
            onChange={(e) => setForm({ ...form, answer: e.target.value })}
            placeholder="答案"
          />
          <Input.TextArea
            rows={2}
            value={form.explanation}
            onChange={(e) => setForm({ ...form, explanation: e.target.value })}
            placeholder="解析"
          />
        </Space>
      </Modal>
    </Card>
  )
}
