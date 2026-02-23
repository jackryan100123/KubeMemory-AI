import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import IncidentDetail from './pages/IncidentDetail'
import GraphExplorer from './pages/GraphExplorer'
import Patterns from './pages/Patterns'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/incidents/:id" element={<IncidentDetail />} />
      <Route path="/graph" element={<GraphExplorer />} />
      <Route path="/patterns" element={<Patterns />} />
    </Routes>
  )
}

export default App
