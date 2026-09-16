import { useEffect, useState } from 'react'
import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Typography,
  Upload,
  message,
} from 'antd'
import { DeleteOutlined, EditOutlined, UploadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Question, QuestionType } from '../types'
import { createQuestion, deleteQuestion, listQuestions, updateQuestion } from '../api/questions'

const TYPE_OPTIONS: Array<{ value: QuestionType; label: string }> = [
  { value: 'choice', label: '选择题' },
  { value: 'fill', label: '填空题' },
  { value: 'tf', label: '判断题' },
  { value: 'short_answer', label: '简答题' },
  { value: 'code', label: '算法设计题' },
]

const emptyForm = {
  type: 'choice' as QuestionType,
  difficulty: 3,
  chapter: '',
  content: '',
  options: { A: '', B: '', C: '', D: '' } as Record<string, string>,
  answer: '',
  explanation: '',
}

export default function QuestionBank() {
  const [items, setItems] = useState<Question[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [filters, setFilters] = useState<{ type?: QuestionType; difficulty?: number; keyword?: string }>({})
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState<Question | null>(null)
  const [creating, setCreating] = useState(false)
  const [form] = Form.useForm()

  async function refresh(p = page, ps = pageSize, f = filters) {
    setLoading(true)
    try {
      const res = await listQuestions({ page: p, page_size: ps, ...f })
      setItems(res.items)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function openEdit(q: Question) {
    setEditing(q)
    setCreating(false)
    form.setFieldsValue({
      ...q,
      options: q.options ?? { A: '', B: '', C: '', D: '' },
    })
  }

  function openCreate() {
    setCreating(true)
    setEditing(null)
    form.setFieldsValue(emptyForm)
  }

  async function submit() {
    const values = await form.validateFields()
    if (values.type === 'choice') {
      values.options = {
        A: values.A ?? '', B: values.B ?? '', C: values.C ?? '', D: values.D ?? '',
      }
    } else {
      values.options = null
    }
    delete values.A
    delete values.B
    delete values.C
    delete values.D
    if (creating) {
      await createQuestion({ ...values, source: 'manual' })
      message.success('已添加')
    } else if (editing) {
      await updateQuestion(editing.id, values)
      message.success('已保存')
    }
    setCreating(false)
    setEditing(null)
    await refresh()
  }

  async function handleDelete(id: number) {
    await deleteQuestion(id)
    message.success('已删除')
    await refresh()
  }

  const columns: ColumnsType<Question> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '题型', dataIndex: 'type', width: 90, render: (t: string) => TYPE_OPTIONS.find((o) => o.value === t)?.label ?? t },
    { title: '难度', dataIndex: 'difficulty', width: 60 },
    { title: '章节', dataIndex: 'chapter', width: 140 },
    { title: '题干', dataIndex: 'content', ellipsis: true },
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_, record) => (
        <>
          <Button size="small" type="link" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Button size="small" type="link" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>
            删除
          </Button>
        </>
      ),
    },
  ]

  return (
    <Card
      title="题库"
      extra={
        <Space wrap>
          <Select
            allowClear
            placeholder="题型"
            style={{ width: 120 }}
            options={TYPE_OPTIONS}
            onChange={(v) => {
              const f = { ...filters, type: v }
              setFilters(f)
              refresh(1, pageSize, f)
            }}
          />
          <Select
            allowClear
            placeholder="难度"
            style={{ width: 100 }}
            options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: `难度${n}` }))}
            onChange={(v) => {
              const f = { ...filters, difficulty: v }
              setFilters(f)
              refresh(1, pageSize, f)
            }}
          />
          <Input.Search
            placeholder="关键词"
            style={{ width: 220 }}
            onSearch={(kw) => {
              const f = { ...filters, keyword: kw || undefined }
              setFilters(f)
              refresh(1, pageSize, f)
            }}
          />
          <Upload
            accept=".json,.xlsx"
            showUploadList={false}
            beforeUpload={async (file) => {
              const fd = new FormData()
              fd.append('file', file)
              const res = await fetch('/api/questions/batch-import', { method: 'POST', body: fd })
              if (res.ok) message.success('批量导入成功')
              else message.error('批量导入失败')
              await refresh()
              return false
            }}
          >
            <Button icon={<UploadOutlined />}>批量导入</Button>
          </Upload>
          <Button type="primary" onClick={openCreate}>
            添加题目
          </Button>
        </Space>
      }
    >
      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        columns={columns}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          onChange: (p, ps) => {
            setPage(p)
            setPageSize(ps)
            refresh(p, ps)
          },
        }}
        locale={{ emptyText: <Typography.Text type="secondary">题库为空。可上传材料抽取题目，或手动添加。</Typography.Text> }}
      />

      <Modal
        open={creating || !!editing}
        title={creating ? '添加题目' : '编辑题目'}
        onCancel={() => {
          setCreating(false)
          setEditing(null)
        }}
        onOk={submit}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Space wrap>
            <Form.Item name="type" label="题型" rules={[{ required: true }]} initialValue="choice">
              <Select style={{ width: 140 }} options={TYPE_OPTIONS} />
            </Form.Item>
            <Form.Item name="difficulty" label="难度(1-5)" initialValue={3}>
              <InputNumber min={1} max={5} />
            </Form.Item>
            <Form.Item name="chapter" label="章节">
              <Input style={{ width: 200 }} placeholder="如：第5章 树和二叉树" />
            </Form.Item>
          </Space>
          <Form.Item name="content" label="题干" rules={[{ required: true, message: '请填写题干' }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(a, b) => a.type !== b.type}>
            {({ getFieldValue }) =>
              getFieldValue('type') === 'choice' ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {(['A', 'B', 'C', 'D'] as const).map((k) => (
                    <Form.Item key={k} name={k} label={`选项 ${k}`}>
                      <Input />
                    </Form.Item>
                  ))}
                </Space>
              ) : null
            }
          </Form.Item>
          <Form.Item name="answer" label="答案" rules={[{ required: true, message: '请填写答案' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="explanation" label="解析">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
