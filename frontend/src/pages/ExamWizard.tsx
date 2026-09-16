import { useEffect, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Input,
  InputNumber,
  Select,
  Space,
  Spin,
  Steps,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import { useNavigate } from 'react-router-dom'
import type { AssembleResponse, ExamDemand, ExamScope, ExamScopeNode, Material, QuestionType } from '../types'
import { listMaterials } from '../api/materials'
import { addScopeNode, confirmScope, deleteScopeNode, getScope, proposeScope, updateScopeNode } from '../api/scopes'
import { generateExam } from '../api/exams'

const TYPE_OPTIONS: Array<{ value: QuestionType; label: string }> = [
  { value: 'choice', label: '选择题' },
  { value: 'fill', label: '填空题' },
  { value: 'tf', label: '判断题' },
  { value: 'short_answer', label: '简答题' },
  { value: 'code', label: '算法设计题' },
]

const DIFF_LABEL: Record<string, string> = {
  choice: '选择题',
  fill: '填空题',
  tf: '判断题',
  short_answer: '简答题',
  code: '算法设计题',
}

const STEPS = ['出卷需求', '考查范围', '试卷']

function defaultDemand(): ExamDemand {
  return {
    title: '',
    duration: 120,
    total_score: 100,
    teaching_progress: '',
    exam_scope: '',
    focus_notes: '',
    material_ids: [],
    question_distribution: { choice: 10, fill: 5, tf: 5, short_answer: 3, code: 2 },
    difficulty_distribution: { '1': 10, '2': 20, '3': 40, '4': 20, '5': 10 },
  }
}

export default function ExamWizard() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [demand, setDemand] = useState<ExamDemand>(defaultDemand)
  const [materials, setMaterials] = useState<Material[]>([])
  const [scope, setScope] = useState<ExamScope | null>(null)
  const [proposing, setProposing] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [assembling, setAssembling] = useState(false)
  const [result, setResult] = useState<AssembleResponse | null>(null)
  const [selectedNode, setSelectedNode] = useState<ExamScopeNode | null>(null)

  useEffect(() => {
    listMaterials().then(setMaterials)
  }, [])

  async function handlePropose() {
    if (!demand.title.trim()) {
      message.warning('请填写试卷名称')
      return
    }
    setProposing(true)
    try {
      const s = await proposeScope(demand)
      setScope(s)
      setStep(1)
      message.success('已生成考查范围，请审核确认')
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setProposing(false)
    }
  }

  async function handleConfirm() {
    if (!scope) return
    setConfirming(true)
    try {
      await confirmScope(scope.id)
      setStep(2)
      message.success('考查范围已确认，开始组卷')
      await runGenerate(scope.id)
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setConfirming(false)
    }
  }

  async function runGenerate(scopeId: number) {
    setAssembling(true)
    try {
      const r = await generateExam({ ...demand, scope_id: scopeId })
      setResult(r)
      message.success(r.summary || '组卷完成')
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setAssembling(false)
    }
  }

  function updateDist(qtype: QuestionType, count: number | null) {
    setDemand((d) => ({
      ...d,
      question_distribution: { ...d.question_distribution, [qtype]: count ?? 0 },
    }))
  }

  function updateDiff(level: string, pct: number | null) {
    setDemand((d) => ({
      ...d,
      difficulty_distribution: { ...d.difficulty_distribution, [level]: pct ?? 0 },
    }))
  }

  async function toggleIncluded(node: ExamScopeNode, included: boolean) {
    if (!scope) return
    await updateScopeNode(scope.id, node.id, { included })
    const s = await getScope(scope.id)
    setScope(s)
  }

  async function addNode() {
    if (!scope) return
    const name = window.prompt('新节点名称')
    if (!name) return
    await addScopeNode(scope.id, {
      parent_id: selectedNode?.id ?? null,
      name,
      node_type: 'point',
    })
    const s = await getScope(scope.id)
    setScope(s)
    message.success('已新增节点')
  }

  async function removeNode(node: ExamScopeNode) {
    if (!scope) return
    await deleteScopeNode(scope.id, node.id)
    const s = await getScope(scope.id)
    setScope(s)
    setSelectedNode(null)
    message.success('已删除节点')
  }

  const scopeTree = scope?.tree ?? []

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card>
        <Steps current={step} items={STEPS.map((t) => ({ title: t }))} />
      </Card>

      {step === 0 && (
        <Card title="出卷需求">
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Space wrap size="middle">
              <div>
                <Typography.Text>试卷名称</Typography.Text>
                <Input
                  style={{ width: 260 }}
                  value={demand.title}
                  onChange={(e) => setDemand({ ...demand, title: e.target.value })}
                  placeholder="如：期中测验"
                />
              </div>
              <div>
                <Typography.Text>时长（分钟）</Typography.Text>
                <InputNumber
                  min={10}
                  max={300}
                  value={demand.duration}
                  onChange={(v) => setDemand({ ...demand, duration: v ?? 120 })}
                />
              </div>
              <div>
                <Typography.Text>总分</Typography.Text>
                <InputNumber
                  min={10}
                  max={1000}
                  value={demand.total_score}
                  onChange={(v) => setDemand({ ...demand, total_score: v ?? 100 })}
                />
              </div>
            </Space>
            <div>
              <Typography.Text strong>教学进度</Typography.Text>
              <Input.TextArea
                rows={2}
                placeholder="如：已讲完第5章树和二叉树"
                value={demand.teaching_progress}
                onChange={(e) => setDemand({ ...demand, teaching_progress: e.target.value })}
              />
            </div>
            <div>
              <Typography.Text strong>考试范围</Typography.Text>
              <Input.TextArea
                rows={2}
                placeholder="如：二叉树遍历、树的性质"
                value={demand.exam_scope}
                onChange={(e) => setDemand({ ...demand, exam_scope: e.target.value })}
              />
            </div>
            <div>
              <Typography.Text strong>重点考查方向</Typography.Text>
              <Input.TextArea
                rows={2}
                placeholder="如：先序遍历的递归实现"
                value={demand.focus_notes}
                onChange={(e) => setDemand({ ...demand, focus_notes: e.target.value })}
              />
            </div>
            <div>
              <Typography.Text strong>题型数量</Typography.Text>
              <Space wrap>
                {TYPE_OPTIONS.map((t) => (
                  <span key={t.value}>
                    {t.label}
                    <InputNumber
                      min={0}
                      size="small"
                      style={{ width: 70, marginLeft: 4 }}
                      value={demand.question_distribution[t.value] ?? 0}
                      onChange={(v) => updateDist(t.value, v)}
                    />
                  </span>
                ))}
              </Space>
            </div>
            <div>
              <Typography.Text strong>难度分布（百分比）</Typography.Text>
              <Space wrap>
                {['1', '2', '3', '4', '5'].map((lv) => (
                  <span key={lv}>
                    难度{lv}
                    <InputNumber
                      min={0}
                      max={100}
                      size="small"
                      style={{ width: 70, marginLeft: 4 }}
                      value={demand.difficulty_distribution[lv] ?? 0}
                      onChange={(v) => updateDiff(lv, v)}
                    />
                  </span>
                ))}
              </Space>
            </div>
            <div>
              <Typography.Text strong>参与材料（可选）</Typography.Text>
              <Select
                mode="multiple"
                style={{ width: '100%' }}
                placeholder="不选则使用全部材料的知识树"
                value={demand.material_ids}
                onChange={(ids) => setDemand({ ...demand, material_ids: ids })}
                options={materials.map((m) => ({ value: m.id, label: m.filename }))}
              />
            </div>
            <Button type="primary" loading={proposing} onClick={handlePropose}>
              生成考查范围
            </Button>
          </Space>
        </Card>
      )}

      {step === 1 && scope && (
        <Card
          title={`考查范围审核（范围 #${scope.id}）`}
          extra={
            <Space>
              <Button onClick={addNode}>新增节点</Button>
              <Button danger disabled={!selectedNode} onClick={() => selectedNode && removeNode(selectedNode)}>
                删除节点
              </Button>
              <Button type="primary" loading={confirming} onClick={handleConfirm}>
                确认考查范围
              </Button>
            </Space>
          }
        >
          <Alert
            type="info"
            showIcon
            message="未确认考查范围不能组卷。取消勾选即排除该节点；确认后范围锁定。"
            style={{ marginBottom: 12 }}
          />
          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ width: 400, flexShrink: 0 }}>
              {scopeTree.length ? (
                scopeTree.map((root) => (
                  <div key={root.id}>
                    <Space>
                      <Checkbox
                        checked={root.included}
                        onChange={(e) => toggleIncluded(root, e.target.checked)}
                      />
                      <Typography.Text strong>{root.name}</Typography.Text>
                    </Space>
                    <div style={{ paddingLeft: 24 }}>
                      {root.children.map((child) => (
                        <div key={child.id}>
                          <Space>
                            <Checkbox
                              checked={child.included}
                              onChange={(e) => toggleIncluded(child, e.target.checked)}
                            />
                            <Button size="small" type="text" onClick={() => setSelectedNode(child)}>
                              {child.name}
                            </Button>
                          </Space>
                          <div style={{ paddingLeft: 24 }}>
                            {child.children.map((pt) => (
                              <Space key={pt.id}>
                                <Checkbox
                                  checked={pt.included}
                                  onChange={(e) => toggleIncluded(pt, e.target.checked)}
                                />
                                <Button size="small" type="text" onClick={() => setSelectedNode(pt)}>
                                  {pt.name}
                                </Button>
                              </Space>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <Typography.Text type="secondary">
                  范围为空，请用「新增节点」补充，或返回上一步调整出卷需求。
                </Typography.Text>
              )}
            </div>
            <Card size="small" title={selectedNode ? `节点：${selectedNode.name}` : '节点详情'} style={{ flex: 1 }}>
              {selectedNode ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Input
                    value={selectedNode.name}
                    onChange={(e) => setSelectedNode({ ...selectedNode, name: e.target.value })}
                  />
                  <Typography.Text type="secondary">概念定义</Typography.Text>
                  <Input.TextArea
                    rows={2}
                    value={selectedNode.definition ?? ''}
                    onChange={(e) => setSelectedNode({ ...selectedNode, definition: e.target.value })}
                  />
                  <Typography.Text type="secondary">解题步骤</Typography.Text>
                  <Input.TextArea
                    rows={2}
                    value={selectedNode.solution_steps ?? ''}
                    onChange={(e) => setSelectedNode({ ...selectedNode, solution_steps: e.target.value })}
                  />
                  <Typography.Text type="secondary">教学重点</Typography.Text>
                  <Input.TextArea
                    rows={2}
                    value={selectedNode.teaching_emphasis ?? ''}
                    onChange={(e) => setSelectedNode({ ...selectedNode, teaching_emphasis: e.target.value })}
                  />
                  <Button
                    type="primary"
                    onClick={async () => {
                      if (!scope || !selectedNode) return
                      await updateScopeNode(scope.id, selectedNode.id, {
                        name: selectedNode.name,
                        definition: selectedNode.definition,
                        solution_steps: selectedNode.solution_steps,
                        teaching_emphasis: selectedNode.teaching_emphasis,
                      })
                      const s = await getScope(scope.id)
                      setScope(s)
                      message.success('已保存')
                    }}
                  >
                    保存修改
                  </Button>
                </Space>
              ) : (
                <Typography.Text type="secondary">选择左侧节点查看与编辑。</Typography.Text>
              )}
            </Card>
          </div>
        </Card>
      )}

      {step === 2 && (
        <Card title="组卷结果">
          {assembling && (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin size="large" />
              <Typography.Paragraph style={{ marginTop: 16 }}>
                检索题库 → 装配 → 缺口写入草稿 → 校验…
              </Typography.Paragraph>
            </div>
          )}
          {!assembling && result && (
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Typography.Paragraph>{result.summary}</Typography.Paragraph>
              {result.drafts.length > 0 && (
                <Alert
                  type="warning"
                  showIcon
                  message={`题库不足，已生成 ${result.drafts.length} 道题目草稿待教师确认`}
                  description={
                    <Space direction="vertical">
                      {Object.entries(result.shortfall).map(([k, v]) => (
                        <Tag key={k}>{`${DIFF_LABEL[k] ?? k} 缺 ${v} 道`}</Tag>
                      ))}
                      <Button size="small" onClick={() => navigate('/drafts')}>
                        去草稿页确认
                      </Button>
                    </Space>
                  }
                />
              )}
              <Table
                rowKey={(q) => String(q.question_id)}
                dataSource={result.questions}
                columns={[
                  { title: '序号', dataIndex: 'sort_order', width: 70 },
                  { title: '题型', dataIndex: 'type', width: 110, render: (t: string) => DIFF_LABEL[t] ?? t },
                  { title: '题干', dataIndex: 'content' },
                  { title: '分值', dataIndex: 'score', width: 70 },
                ]}
                pagination={false}
              />
              <Space>
                <Button type="primary" onClick={() => result && navigate(`/exams/${result.exam_id}`)}>
                  去预览
                </Button>
                <Button onClick={() => navigate('/exams')}>试卷列表</Button>
              </Space>
            </Space>
          )}
          {!assembling && !result && (
            <Typography.Text type="secondary">组卷尚未开始。</Typography.Text>
          )}
        </Card>
      )}
    </Space>
  )
}
