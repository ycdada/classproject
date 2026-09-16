import { Tree } from 'antd'
import type { DataNode } from 'antd/es/tree'

// 课程知识树与考查范围树共用的树形组件
export interface ScopedNodeLike {
  id: number
  name: string
  node_type: string
  included?: boolean
  children: ScopedNodeLike[]
}

export function toTreeData(nodes: ScopedNodeLike[]): DataNode[] {
  return nodes.map((n) => ({
    key: n.id,
    title: n.name,
    children: n.children ? toTreeData(n.children) : undefined,
  }))
}

export default function ScopeTree({
  nodes,
  selectedKeys,
  onSelect,
  checkable = false,
  checkedKeys,
  onCheck,
}: {
  nodes: ScopedNodeLike[]
  selectedKeys?: React.Key[]
  onSelect?: (keys: React.Key[]) => void
  checkable?: boolean
  checkedKeys?: React.Key[]
  onCheck?: (keys: React.Key[]) => void
}) {
  return (
    <Tree
      treeData={toTreeData(nodes)}
      defaultExpandAll
      selectedKeys={selectedKeys}
      onSelect={(keys) => onSelect?.(keys)}
      checkable={checkable}
      checkedKeys={checkedKeys}
      onCheck={(keys) => onCheck?.(keys as React.Key[])}
    />
  )
}
