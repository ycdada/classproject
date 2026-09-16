import { Card, Typography } from 'antd'

export default function Dashboard() {
  return (
    <Card>
      <Typography.Title level={4}>首页</Typography.Title>
      <Typography.Paragraph>
        教师工作台：上传材料、维护知识树与题库、组卷、审核草稿、导出试卷。
      </Typography.Paragraph>
    </Card>
  )
}
