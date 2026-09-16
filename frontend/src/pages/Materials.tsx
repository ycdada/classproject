import { useEffect, useState } from 'react'
import { Button, Select, Table, Upload, message } from 'antd'
import { UploadOutlined, DeleteOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { Link, useNavigate } from 'react-router-dom'
import type { Material, MaterialKind } from '../types'
import { listMaterials, deleteMaterial } from '../api/materials'

const KIND_OPTIONS: Array<{ value: MaterialKind; label: string }> = [
  { value: 'lecture_notes', label: '教案' },
  { value: 'slides', label: 'PPT' },
  { value: 'syllabus', label: '大纲' },
  { value: 'other', label: '其他' },
]

const KIND_LABEL: Record<string, string> = {
  lecture_notes: '教案',
  slides: 'PPT',
  syllabus: '大纲',
  other: '其他',
}

export default function Materials() {
  const [items, setItems] = useState<Material[]>([])
  const [loading, setLoading] = useState(false)
  const [kind, setKind] = useState<MaterialKind>('lecture_notes')
  const navigate = useNavigate()

  async function refresh() {
    setLoading(true)
    try {
      setItems(await listMaterials())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  async function handleUpload(file: File) {
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('kind', kind)
      const res = await fetch('/api/materials/upload', { method: 'POST', body: form })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `上传失败 (${res.status})`)
      }
      message.success('上传成功')
      await refresh()
    } catch (e) {
      message.error((e as Error).message)
    }
    return false
  }

  async function handleDelete(id: number) {
    await deleteMaterial(id)
    message.success('已删除')
    await refresh()
  }

  const columns: ColumnsType<Material> = [
    { title: '文件名', dataIndex: 'filename', key: 'filename' },
    {
      title: '种类',
      dataIndex: 'kind',
      key: 'kind',
      width: 90,
      render: (k: string) => KIND_LABEL[k] ?? k,
    },
    { title: '类型', dataIndex: 'file_type', key: 'file_type', width: 80 },
    { title: '页数', dataIndex: 'page_count', key: 'page_count', width: 70 },
    { title: '上传时间', dataIndex: 'uploaded_at', key: 'uploaded_at', width: 170 },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <>
          <Link to={`/materials/${record.id}`}>详情</Link>
          <Button size="small" type="link" onClick={() => navigate(`/knowledge/${record.id}`)}>
            知识树
          </Button>
          <Button size="small" type="link" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>
            删除
          </Button>
        </>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
        <Select
          value={kind}
          onChange={setKind}
          options={KIND_OPTIONS}
          style={{ width: 140 }}
          aria-label="材料种类"
        />
        <Upload beforeUpload={(file) => handleUpload(file)} showUploadList={false}>
          <Button type="primary" icon={<UploadOutlined />}>上传材料</Button>
        </Upload>
      </div>
      <Table rowKey="id" columns={columns} dataSource={items} loading={loading} />
    </div>
  )
}
