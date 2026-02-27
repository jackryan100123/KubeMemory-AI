import { useCallback, useState, useRef, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import ForceGraph2D from 'react-force-graph-2d'
import { useGraphData } from '../hooks/useGraphData'
import { fetchBlastRadius } from '../api/memory'
import LoadingSpinner from '../components/shared/LoadingSpinner'
import EmptyState from '../components/shared/EmptyState'
import ErrorBoundary from '../components/shared/ErrorBoundary'

const NODE_COLORS = {
  Pod: '#00d4aa',
  Service: '#4f8ef7',
  Incident: '#f7604f',
  Fix: '#f7c94f',
  Node: '#9b59b6',
}

const RELATIONSHIP_LABELS = {
  BELONGS_TO: 'Pod → Service',
  AFFECTED: 'Incident → Pod',
  RESOLVED_BY: 'Incident → Fix (resolution)',
  RUNS_ON: 'Pod → Node',
  TRIGGERED: 'Deployment → Incident',
}

const NAMESPACES = ['default', 'production', 'staging', 'kube-system']

function getNodeName(node, nodes) {
  if (!node) return '—'
  if (typeof node === 'object' && node.name) return node.name
  const found = nodes.find((n) => n.id === node)
  return found?.name ?? String(node).slice(0, 12)
}

function getNodeType(node, nodes) {
  if (!node) return ''
  if (typeof node === 'object' && node.type) return node.type
  const found = nodes.find((n) => n.id === node)
  return found?.type ?? ''
}

function getNamespace() {
  if (typeof window !== 'undefined' && window.__KUBEMEMORY_NS__) return window.__KUBEMEMORY_NS__
  return 'default'
}

export default function GraphExplorer() {
  const [searchParams, setSearchParams] = useSearchParams()
  const namespace = searchParams.get('namespace') || getNamespace()
  const [showPods, setShowPods] = useState(true)
  const [showServices, setShowServices] = useState(true)
  const [showIncidents, setShowIncidents] = useState(true)
  const [showFixes, setShowFixes] = useState(true)
  const [selectedNode, setSelectedNode] = useState(null)
  const [selectedLink, setSelectedLink] = useState(null)
  const [blastRadius, setBlastRadius] = useState(null)
  const [blastLoading, setBlastLoading] = useState(false)
  const containerRef = useRef(null)
  const graphRef = useRef(null)

  const { data, isLoading, error, refetch } = useGraphData(namespace)
  const nodes = data?.nodes ?? []
  const links = data?.links ?? []

  const graphData = useCallback(() => {
    const typeFilter = (t) => {
      if (t === 'Pod' && !showPods) return false
      if (t === 'Service' && !showServices) return false
      if (t === 'Incident' && !showIncidents) return false
      if (t === 'Fix' && !showFixes) return false
      if (t === 'Node') return true
      return true
    }
    const filteredNodes = nodes.filter((n) => typeFilter(n.type))
    const nodeIds = new Set(filteredNodes.map((n) => n.id))
    const filteredLinks = links.filter(
      (l) => nodeIds.has(l.source?.id ?? l.source) && nodeIds.has(l.target?.id ?? l.target)
    )
    return { nodes: filteredNodes, links: filteredLinks }
  }, [nodes, links, showPods, showServices, showIncidents, showFixes])()

  useEffect(() => {
    if (!selectedNode || selectedNode.type !== 'Pod') {
      setBlastRadius(null)
      return
    }
    setBlastLoading(true)
    fetchBlastRadius(selectedNode.name, namespace)
      .then((r) => setBlastRadius(r.blast_radius ?? []))
      .catch(() => setBlastRadius([]))
      .finally(() => setBlastLoading(false))
  }, [selectedNode, namespace])

  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node)
    setSelectedLink(null)
  }, [])

  const handleLinkClick = useCallback((link) => {
    setSelectedLink(link)
    setSelectedNode(null)
  }, [])

  const isLinkSelected = useCallback(
    (link) => {
      if (!selectedLink) return false
      const s = selectedLink.source?.id ?? selectedLink.source
      const t = selectedLink.target?.id ?? selectedLink.target
      const ls = link.source?.id ?? link.source
      const lt = link.target?.id ?? link.target
      return s === ls && t === lt && selectedLink.relationship === link.relationship
    },
    [selectedLink]
  )

  const handleFit = useCallback(() => {
    if (graphRef.current) graphRef.current.zoomToFit(400)
  }, [])

  const handleResetZoom = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.zoom(1)
      graphRef.current.centerAt(0, 0)
    }
  }, [])

  const handleExportPng = useCallback(() => {
    if (!containerRef.current || !graphRef.current) return
    const canvas = containerRef.current.querySelector('canvas')
    if (!canvas) return
    const link = document.createElement('a')
    link.download = `kubememory-graph-${namespace}-${Date.now()}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
  }, [namespace])

  const nodeCanvasObject = useCallback((node, ctx, globalScale) => {
    const label = node.name || node.id || '?'
    const fontSize = Math.max(10, 12 / globalScale)
    const nodeRadius = node.type === 'Incident' ? 6 : 4

    // Node circle
    ctx.beginPath()
    ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI)
    ctx.fillStyle = node.color || NODE_COLORS[node.type] || '#6b7a99'
    ctx.fill()
    ctx.strokeStyle = 'rgba(255,255,255,0.3)'
    ctx.lineWidth = 1 / globalScale
    ctx.stroke()

    // Label always visible (below/right of node to avoid overlap)
    ctx.font = `${fontSize}px system-ui, sans-serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.fillStyle = 'rgba(255,255,255,0.95)'
    const y = node.y + nodeRadius + 2
    ctx.fillText(label.length > 24 ? label.slice(0, 22) + '…' : label, node.x, y)
  }, [])

  if (error) {
    return (
      <div className="p-6">
        <p className="text-accent-red">Failed to load graph.</p>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className="flex flex-col min-h-[calc(100vh-8rem)]">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-4 p-4 border-b border-border bg-surface">
          <span className="font-mono text-muted text-sm">Namespace:</span>
          <select
            value={namespace}
            onChange={(e) => setSearchParams({ namespace: e.target.value })}
            className="rounded border border-border bg-surface2 px-2 py-1 text-sm font-mono text-white"
          >
            {NAMESPACES.map((ns) => (
              <option key={ns} value={ns}>
                {ns}
              </option>
            ))}
          </select>
          <span className="font-mono text-muted text-sm">Show:</span>
          <label className="flex items-center gap-2 text-sm text-white cursor-pointer">
            <input type="checkbox" checked={showPods} onChange={(e) => setShowPods(e.target.checked)} />
            Pods
          </label>
          <label className="flex items-center gap-2 text-sm text-white cursor-pointer">
            <input type="checkbox" checked={showServices} onChange={(e) => setShowServices(e.target.checked)} />
            Services
          </label>
          <label className="flex items-center gap-2 text-sm text-white cursor-pointer">
            <input type="checkbox" checked={showIncidents} onChange={(e) => setShowIncidents(e.target.checked)} />
            Incidents
          </label>
          <label className="flex items-center gap-2 text-sm text-white cursor-pointer">
            <input type="checkbox" checked={showFixes} onChange={(e) => setShowFixes(e.target.checked)} />
            Fixes
          </label>
          <div className="flex items-center gap-4 ml-4 pl-4 border-l border-border">
            <span className="text-muted text-xs font-mono hidden sm:inline">Click nodes or edges</span>
            <div className="flex items-center gap-3 text-xs font-mono">
              {['Pod', 'Service', 'Incident', 'Fix'].map((t) => (
                <span key={t} className="flex items-center gap-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: NODE_COLORS[t] }}
                  />
                  <span className="text-muted">{t}</span>
                </span>
              ))}
            </div>
          </div>
          <div className="flex gap-2 ml-2">
            <button
              type="button"
              onClick={handleFit}
              className="px-3 py-1 rounded border border-border bg-surface2 text-sm font-mono text-white hover:bg-surface"
            >
              Fit to Screen
            </button>
            <button
              type="button"
              onClick={handleResetZoom}
              className="px-3 py-1 rounded border border-border bg-surface2 text-sm font-mono text-white hover:bg-surface"
            >
              Reset Zoom
            </button>
            <button
              type="button"
              onClick={handleExportPng}
              className="px-3 py-1 rounded border border-border bg-surface2 text-sm font-mono text-white hover:bg-surface"
            >
              Export PNG
            </button>
          </div>
        </div>

        <div className="flex-1 flex min-h-0">
          {/* Graph area */}
          <div ref={containerRef} className="flex-1 relative bg-bg min-h-[400px]">
            {isLoading ? (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                <LoadingSpinner className="w-10 h-10" />
                <p className="font-mono text-sm text-muted">Loading graph… (can take up to a minute)</p>
              </div>
            ) : !graphData.nodes.length ? (
              <div className="absolute inset-0 flex items-center justify-center p-6">
                <div className="flex flex-col items-center justify-center max-w-lg text-center">
                  <EmptyState
                    icon="🕸️"
                    title="No graph data for this namespace"
                    description={`The graph is built from incidents (pod crashes, restarts) that the watcher sends to Neo4j. For "${namespace}" there are no Pods/Incidents in the graph yet.`}
                    actionLabel="Refresh"
                    onAction={() => refetch()}
                  />
                  <div className="mt-4 text-left text-muted text-sm font-mono space-y-2 border border-border rounded-lg bg-surface p-4">
                    <p className="font-semibold text-white">Why it’s empty & what to do:</p>
                    <ul className="list-disc list-inside space-y-1">
                      <li>Click <strong>Start watching</strong> in Connect Cluster so the watcher sends pod events.</li>
                      <li>Trigger a pod event (e.g. delete a pod, cause a crash) in this namespace, or seed test data in the backend: <code className="bg-surface2 px-1 rounded">python manage.py seed_test_incidents</code></li>
                      <li>Ensure Celery and Neo4j are running (e.g. <code className="bg-surface2 px-1 rounded">python manage.py verify_memory</code>).</li>
                      <li>Try another namespace from the toolbar if your workloads are in a different one.</li>
                    </ul>
                  </div>
                </div>
              </div>
            ) : (
              <ForceGraph2D
                ref={graphRef}
                graphData={graphData}
                nodeLabel={(n) => `${n.name} (${n.type})`}
                nodeCanvasObject={nodeCanvasObject}
                nodeCanvasObjectMode="replace"
                nodeColor={(n) => NODE_COLORS[n.type] || '#6b7a99'}
                nodeVal={(n) => (n.type === 'Incident' ? 2 : 1)}
                linkColor={(link) => (isLinkSelected(link) ? '#00d4aa' : 'rgba(78, 142, 247, 0.5)')}
                linkWidth={(link) => (isLinkSelected(link) ? 2.5 : 1)}
                linkDirectionalArrowLength={3.5}
                linkDirectionalArrowRelPos={1}
                linkLabel={(link) => RELATIONSHIP_LABELS[link.relationship] || link.relationship || 'relation'}
                onNodeClick={handleNodeClick}
                onLinkClick={handleLinkClick}
                backgroundColor="#0a0c10"
              />
            )}
          </div>

          {/* Side panel: node or edge details */}
          {(selectedNode || selectedLink) && (
            <div className="w-80 shrink-0 border-l border-border bg-surface overflow-y-auto p-4">
              {selectedLink ? (
                <>
                  <h3 className="font-mono font-semibold text-white mb-2 flex items-center gap-2">
                    <span className="text-accent">↔</span> Edge
                  </h3>
                  <div className="space-y-3 text-sm font-mono">
                    <div>
                      <span className="text-muted">Relationship</span>
                      <p className="text-white mt-0.5">
                        {RELATIONSHIP_LABELS[selectedLink.relationship] || selectedLink.relationship}
                      </p>
                    </div>
                    <div>
                      <span className="text-muted">From (source)</span>
                      <p className="text-white mt-0.5 break-all">
                        {getNodeName(selectedLink.source, nodes)} <span className="text-muted">({getNodeType(selectedLink.source, nodes)})</span>
                      </p>
                    </div>
                    <div>
                      <span className="text-muted">To (target)</span>
                      <p className="text-white mt-0.5 break-all">
                        {getNodeName(selectedLink.target, nodes)} <span className="text-muted">({getNodeType(selectedLink.target, nodes)})</span>
                      </p>
                    </div>
                    {selectedLink.relationship === 'RESOLVED_BY' && (
                      <div className="rounded-lg border border-border bg-surface2 p-3">
                        <span className="text-muted text-xs block mb-1">Fix / resolution</span>
                        <p className="text-white text-xs leading-relaxed">
                          {getNodeName(selectedLink.target, nodes)}
                        </p>
                      </div>
                    )}
                    {selectedLink.relationship === 'AFFECTED' && (
                      <p className="text-muted text-xs">This incident affected the pod.</p>
                    )}
                    {selectedLink.relationship === 'BELONGS_TO' && (
                      <p className="text-muted text-xs">Pod is part of this service.</p>
                    )}
                    {selectedLink.relationship === 'RUNS_ON' && (
                      <p className="text-muted text-xs">Pod runs on this node.</p>
                    )}
                    {selectedLink.relationship === 'TRIGGERED' && (
                      <p className="text-muted text-xs">Deployment preceded this incident (within 2h).</p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedLink(null)}
                    className="mt-4 text-xs font-mono text-muted hover:text-white"
                  >
                    Close
                  </button>
                </>
              ) : selectedNode ? (
                <>
                  <h3 className="font-mono font-semibold text-white mb-2">{selectedNode.type}</h3>
                  <p className="text-sm text-muted font-mono break-all">{selectedNode.name}</p>
                  {selectedNode.type === 'Pod' && (
                    <a
                      href={`/?namespace=${namespace}&pod=${encodeURIComponent(selectedNode.name)}`}
                      className="mt-2 inline-block text-xs text-accent hover:underline font-mono"
                    >
                      View incidents for this pod →
                    </a>
                  )}
                  {selectedNode.type === 'Incident' && (
                    <a
                      href={`/incidents/${selectedNode.db_id || selectedNode.id}`}
                      className="mt-2 inline-block text-xs text-accent hover:underline font-mono"
                    >
                      View incident detail →
                    </a>
                  )}
                  {selectedNode.type === 'Fix' && (
                    <p className="mt-2 text-xs text-muted">Fix applied to resolve an incident.</p>
                  )}
                  <button
                    type="button"
                    onClick={() => setSelectedNode(null)}
                    className="mt-4 text-xs font-mono text-muted hover:text-white"
                  >
                    Close
                  </button>
                </>
              ) : null}
            </div>
          )}
        </div>

        {/* Blast radius panel */}
        {selectedNode?.type === 'Pod' && (
          <div className="border-t border-border bg-surface p-4">
            <h4 className="font-mono font-semibold text-white mb-2">BLAST RADIUS</h4>
            {blastLoading ? (
              <LoadingSpinner className="inline-block" />
            ) : !blastRadius?.length ? (
              <p className="text-muted text-sm">No co-occurring incidents in ±5 min.</p>
            ) : (
              <table className="w-full text-sm font-mono">
                <thead>
                  <tr className="text-muted text-left">
                    <th className="py-1 pr-2">Pod</th>
                    <th className="py-1 pr-2">Namespace</th>
                    <th className="py-1 pr-2">Co-occurrence</th>
                    <th className="py-1">Types</th>
                  </tr>
                </thead>
                <tbody className="text-white">
                  {blastRadius.map((row, i) => (
                    <tr key={i}>
                      <td className="py-1 pr-2">{row.affected_pod}</td>
                      <td className="py-1 pr-2">{row.namespace}</td>
                      <td className="py-1 pr-2">{row.co_occurrence}</td>
                      <td className="py-1">{Array.isArray(row.incident_types) ? row.incident_types.join(', ') : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </ErrorBoundary>
  )
}
