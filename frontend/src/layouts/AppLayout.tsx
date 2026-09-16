import { Layout, Menu, Typography } from 'antd'
import {
  HomeOutlined,
  FolderOpenOutlined,
  ApartmentOutlined,
  DatabaseOutlined,
  FormOutlined,
  FileTextOutlined,
  EditOutlined,
} from '@ant-design/icons'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'

const { Sider, Header, Content } = Layout

const ITEMS = [
  { key: '/dashboard', icon: <HomeOutlined />, label: '首页' },
  { key: '/materials', icon: <FolderOpenOutlined />, label: '材料' },
  { key: '/knowledge', icon: <ApartmentOutlined />, label: '知识树' },
  { key: '/questions', icon: <DatabaseOutlined />, label: '题库' },
  { key: '/exams/create', icon: <FormOutlined />, label: '组卷' },
  { key: '/exams', icon: <FileTextOutlined />, label: '试卷' },
  { key: '/drafts', icon: <EditOutlined />, label: '草稿' },
]

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const selected = ITEMS.find((item) => location.pathname.startsWith(item.key))
  const selectedKey = selected?.key ?? (location.pathname.startsWith('/materials') ? '/materials' : '/dashboard')

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={200}>
        <div style={{ padding: '16px 16px 8px' }}>
          <Typography.Title level={5} style={{ color: '#fff', margin: 0 }}>
            数据结构智能出卷
          </Typography.Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={ITEMS}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            borderBottom: '1px solid #f0f0f0',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <Typography.Text strong>教师工作台</Typography.Text>
        </Header>
        <Content style={{ padding: 24, background: '#f5f5f5' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
