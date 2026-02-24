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

function StatusPage() {
  return (
    <div className="p-6">
      <h1 className="font-mono text-xl text-white">Status</h1>
      <p className="text-muted text-sm mt-2">Pipeline and cluster status (placeholder).</p>
    </div>
  )
}

function SettingsPage() {
  return (
    <div className="p-6">
      <h1 className="font-mono text-xl text-white">Settings</h1>
      <p className="text-muted text-sm mt-2">Settings (placeholder).</p>
    </div>
  )
}

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
        <Route path="connect" element={<ClusterConnect />} />
        <Route path="status" element={<StatusPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return <AppContent />
}
