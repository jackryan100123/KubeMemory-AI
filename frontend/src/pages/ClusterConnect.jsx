import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createCluster, testCluster, fetchClusterNamespaces, connectCluster, updateCluster } from '../api/clusters'
import toast from 'react-hot-toast'

const CONNECTION_METHODS = [
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

  const handleGetStarted = () => setStep(2)

  const handleSelectMethod = (id) => {
    setMethod(id)
    setTestResult(null)
    setTestError(null)
  }

  const handleNextFromMethod = () => {
    if (!method) return
    const path = method === 'in_cluster' ? '' : (kubeconfigPath || '~/.kube/config')
    const ctx = method === 'context' ? (contextName || `kind-${clusterName}`) : contextName
    createCluster({
      name: clusterName,
      connection_method: method,
      kubeconfig_path: path,
      context_name: ctx,
      namespaces: [],
    })
      .then((c) => {
        setClusterId(c.id)
        setStep(3)
      })
      .catch((e) => {
        toast.error(e.response?.data?.detail || e.message || 'Failed to create cluster config')
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
      .then(() => {
        toast.success(`Connected to ${clusterName} — watching ${selectedNamespaces.length} namespaces`)
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
            <div className="space-y-2 text-sm">
              <p className="text-white">What we need:</p>
              <ul className="list-disc list-inside text-muted space-y-1">
                <li>Read pods, events, namespaces</li>
                <li className="text-red-400/80">No write access</li>
                <li className="text-red-400/80">No secrets access</li>
                <li className="text-red-400/80">No cluster-admin</li>
              </ul>
            </div>
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
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
                disabled={!method}
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
                  placeholder="kubememory-prod-sim"
                />
              </div>
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
              {(method === 'context' || method === 'kubeconfig') && (
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
