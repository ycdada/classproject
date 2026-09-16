import { useEffect, useState } from 'react'
import {
  Button,
  Card,
  Input,
  InputNumber,
  Select,
  Space,
  Spin,
  Typography,
  message,
} from 'antd'
import { useParams } from 'react-router-dom'
import type { Exam, ExamQuestionItem, QuestionType } from '../types'
import { exportAnswerSheet, exportExam, getExam, updateExamQuestion } from '../api/exams'

const TYPE_LABEL: Record<string, string> = {
  choice: '选择题',
  fill: '填空题',
  tf: '判断题',
  short_answer: '简答题',
  code: '算法设计题',
}

const TYPE_OPTIONS = Object.entries(TYPE_LABEL).map(([value, label]) => ({ value, label }))

export default function ExamPreview() {
  const { id } = useParams()
  const examId = Number(id)
  const [exam, setExam] = useState<Exam | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  async function load() {
    setLoading(true)
    try {
      setExam(await getExam(examId))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examId])

  async function patchQuestion(eq: ExamQuestionItem, data: Record<string, unknown>) {
    setSaving(true)
    try {
      await updateExamQuestion(examId, eq.eq_id, data)
      await load()
      message.success('已保存')
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  function move(eq: ExamQuestionItem, dir: -1 | 1) {
    if (!exam) return
    const sorted = [...exam.questions].sort((a, b) => a.sort_order - b.sort_order)
    const idx = sorted.findIndex((q) => q.eq_id === eq.eq_id)
    const target = sorted[idx + dir]
    if (!target) return
    Promise.all([
      updateExamQuestion(examId, eq.eq_id, { sort_order: target.sort_order }),
      updateExamQuestion(examId, target.eq_id, { sort_order: eq.sort_order }),
    ]).then(load)
  }

  async function download(kind: 'docx' | 'pdf' | 'txt', withAnswer: boolean) {
    try {
      await exportExam(examId, kind, withAnswer)
    } catch (e) {
      message.error((e as Error).message)
    }
  }

  if (loading) return <Spin />
  if (!exam) return <Card>试卷不存在</Card>

  const questions = [...exam.questions].sort((a, b) => a.sort_order - b.sort_order)

  return (
    <Card
      title={`${exam.title}（总分 ${exam.total_score}｜时长 ${exam.duration} 分钟）`}
      extra={
        <Space wrap>
          <Button onClick={() => download('docx', false)}>导出 DOCX</Button>
          <Button onClick={() => download('docx', true)}>导出 DOCX（含答案）</Button>
          <Button onClick={() => download('pdf', false)}>导出 PDF</Button>
          <Button onClick={() => download('txt', false)}>导出 TXT</Button>
          <Button onClick={() => exportAnswerSheet(examId)}>导出答题卡</Button>
        </Space>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {questions.map((eq, i) => (
          <Card
            key={eq.eq_id}
            size="small"
            type="inner"
            title={`第 ${i + 1} 题（${TYPE_LABEL[eq.type] ?? eq.type}｜${eq.score} 分）`}
            extra={
              <Space>
                <Button size="small" onClick={() => move(eq, -1)}>上移</Button>
                <Button size="small" onClick={() => move(eq, 1)}>下移</Button>
              </Space>
            }
          >
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Input.TextArea
                rows={2}
                defaultValue={eq.content}
                onBlur={(e) => e.target.value !== eq.content && patchQuestion(eq, { content: e.target.value })}
              />
              {eq.options && (
                <Space wrap>
                  {Object.entries(eq.options).map(([k, v]) => (
                    <span key={k}>
                      {k}.
                      <Input
                        style={{ width: 180 }}
                        defaultValue={v}
                        onBlur={(e) =>
                          e.target.value !== v &&
                          patchQuestion(eq, { options: { ...eq.options, [k]: e.target.value } })
                        }
                      />
                    </span>
                  ))}
                </Space>
              )}
              <Space wrap>
                <Select
                  style={{ width: 120 }}
                  value={(eq.type as QuestionType) ?? undefined}
                  options={TYPE_OPTIONS}
                  onChange={(t) => patchQuestion(eq, { type: t })}
                />
                <span>
                  分值
                  <InputNumber
                    min={1}
                    style={{ width: 70, marginLeft: 4 }}
                    defaultValue={eq.score}
                    onBlur={(e) => {
                      const v = Number((e.target as HTMLInputElement).value)
                      if (v && v !== eq.score) patchQuestion(eq, { score: v })
                    }}
                  />
                </span>
                <span>
                  答案
                  <Input
                    style={{ width: 140, marginLeft: 4 }}
                    defaultValue={eq.answer}
                    onBlur={(e) => e.target.value !== eq.answer && patchQuestion(eq, { answer: e.target.value })}
                  />
                </span>
              </Space>
              <Typography.Text type="secondary">解析</Typography.Text>
              <Input.TextArea
                rows={1}
                defaultValue={eq.explanation}
                onBlur={(e) =>
                  e.target.value !== eq.explanation && patchQuestion(eq, { explanation: e.target.value })
                }
              />
            </Space>
          </Card>
        ))}
        {!questions.length && (
          <Typography.Text type="secondary">这份试卷还没有题目。</Typography.Text>
        )}
        <Typography.Text type="secondary">
          {saving ? '保存中…' : '修改题干 / 选项 / 答案 / 解析 / 分值后失焦即保存；上移下移即时生效。'}
        </Typography.Text>
      </Space>
    </Card>
  )
}
