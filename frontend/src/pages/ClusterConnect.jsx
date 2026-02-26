import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { createCluster, testCluster, fetchClusterNamespaces, connectCluster, updateCluster, fetchClusterSecurityInfo } from '../api/clusters'
import toast from 'react-hot-toast'

const CONNECTION_METHODS = [
  { id: 'paste', label: 'Paste kubeconfig', desc: 'Easiest: paste YAML, we save it. Works with Minikube/Kind.', icon: '📋' },
  { id: 'kubeconfig', label: 'Kubeconfig File Path', desc: 'For: any remote cluster', icon: '📁' },
  { id: 'context', label: 'Kind / Local (Auto-detect)', desc: 'For: local dev Kind/Minikube', icon: '⎈' },
  { id: 'in_cluster', label: 'In-Cluster', desc: 'For: production deployments', icon: '🔧' },
]

export default function ClusterConnect() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [method, setMethod] = useState('')
  const [clusterName, setClusterName] = useState('kubememory-prod-sim')
  const [kubeconfigPath, setKubeconfigPath] = useState('')
  const [contextName, setContextName] = useState('')
  const [clusterId, setClusterId] = useState(null)
  const [testResult, setTestResult] = useState(null)
  const [testError, setTestError] = useState(null)
  const [testing, setTesting] = useState(false)
  const [namespaces, setNamespaces] = useState([])
  const [selectedNamespaces, setSelectedNamespaces] = useState([])
  const [loadingNamespaces, setLoadingNamespaces] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [kubeconfigPaste, setKubeconfigPaste] = useState('')
  const [useDockerHost, setUseDockerHost] = useState(true)
  const [securityInfo, setSecurityInfo] = useState(null)
  const [securityOpen, setSecurityOpen] = useState(false)

  useEffect(() => {
    fetchClusterSecurityInfo()
      .then(setSecurityInfo)
      .catch(() => setSecurityInfo(null))
  }, [])

  const handleGetStarted = () => setStep(2)

  const handleSelectMethod = (id) => {
    setMethod(id)
    setTestResult(null)
    setTestError(null)
  }

  const formatApiError = (e) => {
    const data = e.response?.data
    if (!data) return e.message || 'Request failed'
    if (typeof data.detail === 'string') return data.detail
    if (typeof data === 'string') return data
    if (data.error) return data.error
    const parts = []
    for (const [key, val] of Object.entries(data)) {
      const msg = Array.isArray(val) ? val.join(' ') : String(val)
      if (msg) parts.push(key === 'non_field_errors' ? msg : `${key}: ${msg}`)
    }
    return parts.length ? parts.join('; ') : (e.message || 'Validation failed')
  }

  const handleNextFromMethod = () => {
    if (!method) return
    const path = method === 'in_cluster' ? '' : (method === 'paste' ? '' : (kubeconfigPath || '~/.kube/config'))
    const ctx = method === 'context' ? (contextName || `kind-${clusterName}`) : (contextName || '')
    const payload = {
      name: (clusterName || '').trim() || (method === 'paste' ? 'minikube' : 'kubememory-prod-sim'),
      connection_method: 'kubeconfig',
      kubeconfig_path: path,
      context_name: ctx,
      namespaces: [],
    }
    if (method === 'paste') {
      const content = (kubeconfigPaste || '').trim()
      if (!content) {
        toast.error('Paste your kubeconfig YAML (e.g. from: kubectl config view --minify --raw)')
        return
      }
      payload.kubeconfig_content = content
      payload.use_docker_host = useDockerHost
    }
    createCluster(payload)
      .then((c) => {
        setClusterId(c.id)
        setStep(3)
      })
      .catch((e) => {
        toast.error(formatApiError(e))
      })
  }

  const handleTestConnection = () => {
    if (!clusterId) return
    setTesting(true)
    setTestError(null)
    setTestResult(null)
    testCluster(clusterId)
      .then((res) => {
        setTestResult(res)
        if (res.connected) setTestError(null)
        else setTestError(res.error || 'Connection failed')
      })
      .catch((e) => {
        setTestError(e.response?.data?.error || e.message || 'Connection failed')
        setTestResult({ connected: false })
      })
      .finally(() => setTesting(false))
  }

  const handleNextFromTest = () => {
    if (testResult?.connected) {
      setStep(4)
      setLoadingNamespaces(true)
      fetchClusterNamespaces(clusterId)
        .then((res) => {
          const list = res.namespaces || []
          setNamespaces(list)
          setSelectedNamespaces(list.filter((n) => !n.includes('kube-system')))
        })
        .catch(() => setNamespaces([]))
        .finally(() => setLoadingNamespaces(false))
    }
  }

  const toggleNamespace = (ns) => {
    setSelectedNamespaces((prev) =>
      prev.includes(ns) ? prev.filter((n) => n !== ns) : [...prev, ns]
    )
  }

  const handleStartWatching = () => {
    if (!clusterId) return
    setConnecting(true)
    updateCluster(clusterId, { namespaces: selectedNamespaces })
      .then(() => connectCluster(clusterId))
      .then((res) => {
        const watcherStarted = res?.watcher_started === true
        toast.success(
          watcherStarted
            ? `Connected to ${clusterName}. Watcher started — watching ${selectedNamespaces.length} namespaces.`
            : `Connected to ${clusterName} — watching ${selectedNamespaces.length} namespaces.${res?.watcher_error ? ` (Watcher: ${res.watcher_error})` : ''}`
        )
        navigate('/')
      })
      .catch((e) => toast.error(e.response?.data?.detail || e.message || 'Connect failed'))
      .finally(() => setConnecting(false))
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="rounded-lg border border-border bg-surface p-6 space-y-6">
        {step === 1 && (
          <>
            <h1 className="text-xl font-mono font-bold text-white">⎈ Connect Your Cluster</h1>
            <p className="text-muted text-sm">
              KubeMemory needs read-only access to your cluster to watch events. It NEVER modifies anything.
            </p>
            <button
              type="button"
              onClick={() => setSecurityOpen(!securityOpen)}
              className="flex items-center gap-2 text-sm font-mono text-accent hover:underline"
            >
              {securityOpen ? '▼' : '▶'} Security & what we access
            </button>
            {securityOpen && securityInfo && (
              <div className="rounded-lg border border-border bg-surface2 p-4 text-sm space-y-3">
                <p className="font-mono font-semibold text-white">{securityInfo.title}</p>
                <p className="text-muted">We only read. We never write, delete, or access secrets.</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <p className="text-red-400/90 font-mono text-xs uppercase mb-1">We never</p>
                    <ul className="list-disc list-inside text-muted space-y-0.5">
                      {securityInfo.we_never?.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-accent font-mono text-xs uppercase mb-1">We do</p>
                    <ul className="list-disc list-inside text-muted space-y-0.5">
                      {securityInfo.we_do?.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
                <p className="text-muted text-xs">Recommendations: {securityInfo.recommendations?.join(' ')}</p>
              </div>
            )}
            <button
              type="button"
              onClick={handleGetStarted}
              className="px-4 py-2 rounded bg-accent text-bg font-mono font-semibold hover:opacity-90"
            >
              GET STARTED →
            </button>
          </>
        )}

        {step === 2 && (
          <>
            <h2 className="font-mono font-semibold text-white">Connection Method</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {CONNECTION_METHODS.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => handleSelectMethod(m.id)}
                  className={`p-4 rounded-lg border text-left transition-colors ${
                    method === m.id
                      ? 'border-accent bg-accent/10 text-white'
                      : 'border-border bg-surface2 text-muted hover:text-white'
                  }`}
                >
                  <span className="text-2xl block mb-2">{m.icon}</span>
                  <span className="font-mono text-sm block">{m.label}</span>
                  <span className="text-xs mt-1 opacity-80">{m.desc}</span>
                </button>
              ))}
            </div>
            {method === 'paste' && (
              <div className="space-y-3 rounded border border-border bg-surface2 p-4">
                <div>
                  <label className="block text-xs font-mono text-muted mb-1">Cluster name</label>
                  <input
                    type="text"
                    value={clusterName}
                    onChange={(e) => setClusterName(e.target.value)}
                    className="w-full rounded border border-border bg-surface px-3 py-2 text-white font-mono"
                    placeholder="minikube"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono text-muted mb-1">Kubeconfig YAML (paste from: kubectl config view --minify --raw)</label>
                  <textarea
                    value={kubeconfigPaste}
                    onChange={(e) => setKubeconfigPaste(e.target.value)}
                    placeholder="apiVersion: v1\nclusters:\n  - cluster:\n      server: https://..."
                    rows={8}
                    className="w-full rounded border border-border bg-surface px-3 py-2 text-white font-mono text-sm"
                  />
                </div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useDockerHost}
                    onChange={(e) => setUseDockerHost(e.target.checked)}
                    className="rounded border-border"
                  />
                  <span className="text-sm font-mono text-muted">App is running in Docker (use host.docker.internal so the container can reach Minikube/Kind)</span>
                </label>
              </div>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="px-3 py-1.5 rounded border border-border text-muted font-mono text-sm"
              >
                ← Back
              </button>
              <button
                type="button"
                onClick={handleNextFromMethod}
                disabled={!method || (method === 'paste' && !kubeconfigPaste.trim())}
                className="px-4 py-2 rounded bg-accent text-bg font-mono font-semibold hover:opacity-90 disabled:opacity-50"
              >
                NEXT →
              </button>
            </div>
          </>
        )}

        {step === 3 && (
          <>
            <h2 className="font-mono font-semibold text-white">Configure & Test</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-muted mb-1">Cluster Name</label>
                <input
                  type="text"
                  value={clusterName}
                  onChange={(e) => setClusterName(e.target.value)}
                  className="w-full rounded border border-border bg-surface2 px-3 py-2 text-white font-mono"
                  placeholder="minikube"
                />
              </div>
              {method === 'paste' && (
                <p className="text-xs text-muted">Kubeconfig was saved. Test the connection below.</p>
              )}
              {method === 'kubeconfig' && (
                <div>
                  <label className="block text-xs font-mono text-muted mb-1">Kubeconfig Path</label>
                  <input
                    type="text"
                    value={kubeconfigPath}
                    onChange={(e) => setKubeconfigPath(e.target.value)}
                    className="w-full rounded border border-border bg-surface2 px-3 py-2 text-white font-mono"
                    placeholder="~/.kube/config"
                  />
                </div>
              )}
              {(method === 'context' || method === 'kubeconfig') && method !== 'paste' && (
                <div>
                  <label className="block text-xs font-mono text-muted mb-1">Context (optional)</label>
                  <input
                    type="text"
                    value={contextName}
                    onChange={(e) => setContextName(e.target.value)}
                    className="w-full rounded border border-border bg-surface2 px-3 py-2 text-white font-mono"
                    placeholder={method === 'context' ? 'kind-kubememory-prod-sim' : ''}
                  />
                </div>
              )}
              {method === 'context' && (
                <p className="text-xs text-muted">
                  Kubeconfig will be loaded from ~/.kube/config (context: {contextName || `kind-${clusterName}`})
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testing || !clusterId}
              className="px-4 py-2 rounded border border-accent text-accent font-mono text-sm hover:bg-accent/10 disabled:opacity-50"
            >
              {testing ? 'Testing…' : 'TEST CONNECTION'}
            </button>
            {testError && (
              <div className="rounded border border-red-500/50 bg-red-500/10 p-4 text-sm">
                <p className="font-mono text-red-400 font-semibold">✗ Connection Failed</p>
                <p className="text-muted mt-1">{testError}</p>
                <p className="text-xs text-muted mt-2">Common fixes:</p>
                <ul className="list-disc list-inside text-xs text-muted mt-1">
                  <li>Is Docker running? docker ps</li>
                  <li>Is your cluster up? kind get clusters</li>
                  <li>Check kubeconfig: kubectl config current-context</li>
                </ul>
              </div>
            )}
            {testResult?.connected && (
              <div className="rounded border border-accent/50 bg-accent/10 p-4 text-sm">
                <p className="font-mono text-accent font-semibold">✓ Connected!</p>
                <p className="text-muted mt-1">
                  {testResult.node_count} nodes • K8s {testResult.server_version || 'unknown'}
                </p>
                <p className="text-xs text-muted mt-1">Permissions verified (read-only)</p>
              </div>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="px-3 py-1.5 rounded border border-border text-muted font-mono text-sm"
              >
                ← BACK
              </button>
              <button
                type="button"
                onClick={handleNextFromTest}
                disabled={!testResult?.connected}
                className="px-4 py-2 rounded bg-accent text-bg font-mono font-semibold hover:opacity-90 disabled:opacity-50"
              >
                NEXT →
              </button>
            </div>
          </>
        )}

        {step === 4 && (
          <>
            <h2 className="font-mono font-semibold text-white">Which namespaces should KubeMemory watch?</h2>
            {loadingNamespaces ? (
              <p className="text-muted">Loading namespaces…</p>
            ) : (
              <div className="space-y-2">
                {namespaces.map((ns) => (
                  <label key={ns} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedNamespaces.includes(ns)}
                      onChange={() => toggleNamespace(ns)}
                      className="rounded border-border"
                    />
                    <span className="font-mono text-sm text-white">
                      {ns}
                      {ns === 'kube-system' && ' (system — not recommended)'}
                    </span>
                  </label>
                ))}
              </div>
            )}
            <p className="text-xs text-muted">Tip: Avoid kube-system — high noise, low signal</p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(3)}
                className="px-3 py-1.5 rounded border border-border text-muted font-mono text-sm"
              >
                ← BACK
              </button>
              <button
                type="button"
                onClick={handleStartWatching}
                disabled={connecting || selectedNamespaces.length === 0}
                className="px-4 py-2 rounded bg-accent text-bg font-mono font-semibold hover:opacity-90 disabled:opacity-50"
              >
                {connecting ? 'Connecting…' : 'START WATCHING ✓'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
