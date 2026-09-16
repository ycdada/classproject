import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Descriptions, Input, Select, Space, Spin, Typography, message } from 'antd'
import { useParams, Link } from 'react-router-dom'
import type { KnowledgeNode } from '../types'
import { extractTree, getTree, updateNode, deleteTree } from '../api/knowledge'
import { listMaterials } from '../api/materials'
import ScopeTree from '../components/ScopeTree'

export default function KnowledgeTreePage() {
  const { materialId } = useParams()
  const [materials, setMaterials] = useState<Array<{ id: number; filename: string }>>([])
  const [current, setCurrent] = useState<number | null>(materialId ? Number(materialId) : null)
  const [tree, setTree] = useState<KnowledgeNode[]>([])
  const [loading, setLoading] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [selected, setSelected] = useState<KnowledgeNode | null>(null)

  useEffect(() => {
    listMaterials().then(setMaterials)
  }, [])

  useEffect(() => {
    if (materialId) setCurrent(Number(materialId))
  }, [materialId])

  const loadTree = async (mid: number) => {
    setLoading(true)
    try {
      setTree(await getTree(mid))
      setSelected(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (current) loadTree(current)
  }, [current])

  async function handleExtract() {
    if (!current) return
    setExtracting(true)
    try {
      const res = await fetch(`/api/knowledge/extract/${current}`, { method: 'POST' })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `提取失败 (${res.status})`)
      }
      message.success('提取完成')
      await loadTree(current)
    } catch (e) {
      message.error((e as Error).message)
    } finally {
      setExtracting(false)
    }
  }

  async function handleReextract() {
    if (!current) return
    await deleteTree(current)
    await handleExtract()
  }

  async function saveSelected() {
    if (!selected) return
    await updateNode(selected.id, {
      name: selected.name,
      definition: selected.definition,
      key_terms: selected.key_terms,
      teaching_emphasis: selected.teaching_emphasis,
      solution_steps: selected.solution_steps,
    })
    message.success('已保存')
    if (current) await loadTree(current)
  }

  const detail = useMemo(() => selected, [selected])

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card size="small">
        <Space wrap>
          <Select
            style={{ width: 300 }}
            placeholder="选择材料"
            value={current}
            onChange={(v) => setCurrent(v)}
            options={materials.map((m) => ({ value: m.id, label: m.filename }))}
          />
          <Button type="primary" loading={extracting} disabled={!current} onClick={handleExtract}>
            提取知识树
          </Button>
          <Button disabled={!current} onClick={handleReextract}>
            重新提取
          </Button>
        </Space>
      </Card>
      <div style={{ display: 'flex', gap: 16 }}>
        <Card title="知识树" style={{ width: 380, flexShrink: 0 }} loading={loading}>
          {tree.length ? (
            <ScopeTree
              nodes={tree}
              selectedKeys={selected ? [selected.id] : []}
              onSelect={(keys) => {
                const id = keys[0]
                const flat: KnowledgeNode[] = []
                const walk = (nodes: KnowledgeNode[]) => {
                  nodes.forEach((n) => {
                    flat.push(n)
                    walk(n.children)
                  })
                }
                walk(tree)
                setSelected(flat.find((n) => n.id === id) ?? null)
              }}
            />
          ) : (
            <Typography.Text type="secondary">
              尚无知识树。选择材料后点「提取知识树」。
            </Typography.Text>
          )}
        </Card>
        <Card title="节点详情" style={{ flex: 1 }}>
          {detail ? (
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <Descriptions size="small" column={2}>
                <Descriptions.Item label="类型">{detail.node_type}</Descriptions.Item>
                <Descriptions.Item label="名称">
                  <Input
                    value={detail.name}
                    onChange={(e) => setSelected({ ...detail, name: e.target.value })}
                  />
                </Descriptions.Item>
              </Descriptions>
              <Typography.Text type="secondary">概念定义</Typography.Text>
              <Input.TextArea
                rows={2}
                value={detail.definition ?? ''}
                onChange={(e) => setSelected({ ...detail, definition: e.target.value })}
              />
              <Typography.Text type="secondary">专业术语（逗号分隔）</Typography.Text>
              <Input
                value={(detail.key_terms ?? []).join(', ')}
                onChange={(e) =>
                  setSelected({
                    ...detail,
                    key_terms: e.target.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
                  })
                }
              />
              <Typography.Text type="secondary">解题步骤</Typography.Text>
              <Input.TextArea
                rows={3}
                value={detail.solution_steps ?? ''}
                onChange={(e) => setSelected({ ...detail, solution_steps: e.target.value })}
              />
              <Typography.Text type="secondary">教学重点</Typography.Text>
              <Input.TextArea
                rows={2}
                value={detail.teaching_emphasis ?? ''}
                onChange={(e) => setSelected({ ...detail, teaching_emphasis: e.target.value })}
              />
              <Button type="primary" onClick={saveSelected}>
                保存修改
              </Button>
            </Space>
          ) : (
            <Typography.Text type="secondary">在左侧选择一个知识点查看与编辑。</Typography.Text>
          )}
        </Card>
      </div>
    </Space>
  )
}
