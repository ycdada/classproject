import { useEffect, useState } from 'react'
import { Card, Col, Row, Statistic, Typography } from 'antd'
import { Link } from 'react-router-dom'
import { listMaterials } from '../api/materials'
import { listQuestions } from '../api/questions'
import { listExams } from '../api/exams'
import { listDrafts } from '../api/drafts'
import ChatDock from '../components/ChatDock'

export default function Dashboard() {
  const [stats, setStats] = useState({ materials: 0, questions: 0, exams: 0, pendingDrafts: 0 })

  useEffect(() => {
    async function load() {
      try {
        const [materials, questions, exams, drafts] = await Promise.all([
          listMaterials(),
          listQuestions({ page: 1, page_size: 1 }),
          listExams(),
          listDrafts('pending'),
        ])
        setStats({
          materials: materials.length,
          questions: questions.total,
          exams: exams.length,
          pendingDrafts: drafts.length,
        })
      } catch {
        /* backend not ready */
      }
    }
    load()
  }, [])

  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Card>
          <Typography.Title level={4} style={{ marginTop: 0 }}>
            数据结构智能出卷系统
          </Typography.Title>
          <Typography.Paragraph type="secondary">
            上传课程材料 → 抽取知识树（含解题步骤）→ 填写出卷需求 → 确认考查范围 → 组卷 →
            审核题目草稿 → 预览导出试卷。
          </Typography.Paragraph>
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic title="课程材料" value={stats.materials} />
          <Link to="/materials">进入课程材料库</Link>
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic title="题库题目" value={stats.questions} />
          <Link to="/questions">进入题库</Link>
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic title="待审核草稿" value={stats.pendingDrafts} />
          <Link to="/drafts">去草稿页审核</Link>
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic title="已生成试卷" value={stats.exams} />
          <Link to="/exams">查看试卷列表</Link>
        </Card>
      </Col>
      <Col span={24}>
        <Card title="教学助手" styles={{ body: { padding: 0 } }}>
          <ChatDock embedded />
        </Card>
      </Col>
    </Row>
  )
}
