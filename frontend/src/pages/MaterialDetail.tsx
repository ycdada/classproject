import { useEffect, useState } from 'react'
import { Card, Typography, Spin } from 'antd'
import { useParams } from 'react-router-dom'
import type { Material } from '../types'
import { getMaterial } from '../api/materials'

const KIND_LABEL: Record<string, string> = {
  lecture_notes: '教案',
  slides: 'PPT',
  syllabus: '大纲',
  other: '其他',
}

export default function MaterialDetail() {
  const { id } = useParams()
  const [material, setMaterial] = useState<Material | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    getMaterial(Number(id))
      .then(setMaterial)
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <Spin />
  if (!material) return <Card>材料不存在</Card>

  return (
    <Card title={material.filename} extra={<Typography.Text type="secondary">种类：{KIND_LABEL[material.kind] ?? material.kind}</Typography.Text>}>
      <Typography.Paragraph type="secondary">
        上传时间：{material.uploaded_at} ｜ 页数：{material.page_count}
      </Typography.Paragraph>
      <Typography.Paragraph>
        <pre style={{ whiteSpace: 'pre-wrap', maxHeight: '60vh', overflow: 'auto' }}>
          {material.content_md || '（未解析出正文）'}
        </pre>
      </Typography.Paragraph>
    </Card>
  )
}
