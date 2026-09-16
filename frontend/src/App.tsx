import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import Dashboard from './pages/Dashboard'
import Materials from './pages/Materials'
import MaterialDetail from './pages/MaterialDetail'
import KnowledgeTree from './pages/KnowledgeTree'
import QuestionBank from './pages/QuestionBank'
import ExamWizard from './pages/ExamWizard'
import ExamList from './pages/ExamList'
import ExamPreview from './pages/ExamPreview'
import Drafts from './pages/Drafts'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/materials" element={<Materials />} />
        <Route path="/materials/:id" element={<MaterialDetail />} />
        <Route path="/knowledge/:materialId" element={<KnowledgeTree />} />
        <Route path="/knowledge" element={<KnowledgeTree />} />
        <Route path="/questions" element={<QuestionBank />} />
        <Route path="/exams/create" element={<ExamWizard />} />
        <Route path="/exams" element={<ExamList />} />
        <Route path="/exams/:id" element={<ExamPreview />} />
        <Route path="/exams/:id/review" element={<ExamPreview />} />
        <Route path="/drafts" element={<Drafts />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  )
}
