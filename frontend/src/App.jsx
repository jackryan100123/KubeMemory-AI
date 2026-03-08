import { Routes, Route, Navigate } from 'react-router-dom'
import { useWebSocket } from './hooks/useWebSocket'
import AppShell from './components/layout/AppShell'
import Dashboard from './pages/Dashboard'
import IncidentsList from './pages/IncidentsList'
import IncidentDetail from './pages/IncidentDetail'
import GraphExplorer from './pages/GraphExplorer'
import Patterns from './pages/Patterns'
import ClusterConnect from './pages/ClusterConnect'
import RiskCheck from './pages/RiskCheck'
import Chat from './pages/Chat'
import Status from './pages/Status'
import Settings from './pages/Settings'

function AppContent() {
  useWebSocket()
  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<Dashboard />} />
        <Route path="incidents" element={<IncidentsList />} />
        <Route path="incidents/:id" element={<IncidentDetail />} />
        <Route path="graph" element={<GraphExplorer />} />
        <Route path="patterns" element={<Patterns />} />
        <Route path="risk-check" element={<RiskCheck />} />
        <Route path="chat" element={<Chat />} />
        <Route path="chat/:sessionId" element={<Chat />} />
        <Route path="connect" element={<ClusterConnect />} />
        <Route path="status" element={<Status />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return <AppContent />
}
