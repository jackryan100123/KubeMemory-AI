import { Routes, Route, Navigate } from 'react-router-dom'
import RequireAuth from './components/auth/RequireAuth'
import AppShell from './components/layout/AppShell'
import Login from './pages/Login'
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
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
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
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return <AppContent />
}
