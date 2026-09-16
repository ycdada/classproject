import { useEffect, useState } from 'react'
import { Button, Card, Table, Typography, message } from 'antd'
import { Link, useNavigate } from 'react-router-dom'
import type { Exam } from '../types'
import { deleteExam, listExams } from '../api/exams'

export default function ExamListPage() {
  const [exams, setExams] = useState<Exam[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function refresh() {
    setLoading(true)
    try {
      setExams(await listExams())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  async function handleDelete(id: number) {
    await deleteExam(id)
    message.success('已删除')
    await refresh()
  }

  return (
    <Card title="试卷列表" extra={<Button type="primary" onClick={() => navigate('/exams/create')}>去组卷</Button>}>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={exams}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 70 },
          { title: '标题', dataIndex: 'title' },
          { title: '总分', dataIndex: 'total_score', width: 80 },
          { title: '时长', dataIndex: 'duration', width: 90, render: (v: number) => `${v} 分钟` },
          { title: '状态', dataIndex: 'status', width: 90 },
          { title: '创建时间', dataIndex: 'created_at', width: 180 },
          {
            title: '操作',
            key: 'action',
            width: 180,
            render: (_, record) => (
              <>
                <Link to={`/exams/${record.id}`}>预览</Link>
                <Button size="small" type="link" danger onClick={() => handleDelete(record.id)}>
                  删除
                </Button>
              </>
            ),
          },
        ]}
        locale={{ emptyText: <Typography.Text type="secondary">还没有试卷，去「组卷」生成一份。</Typography.Text> }}
      />
    </Card>
  )
}
