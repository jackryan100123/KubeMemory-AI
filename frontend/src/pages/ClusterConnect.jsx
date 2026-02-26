import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { createCluster, testCluster, fetchClusterNamespaces, connectCluster, updateCluster, fetchClusterSecurityInfo } from '../api/clusters'
import toast from 'react-hot-toast'

const WORKFLOWS = [
  {
    id: 'paste',
    title: 'Paste kubeconfig',
    subtitle: 'I have an existing cluster and can copy my config',
    icon: '📋',
    bestFor: 'Kind, Minikube, or any cluster where you can run kubectl',
  },
  {
    id: 'kubeconfig',
    title: 'Kubeconfig file path',
    subtitle: 'I have a config file (e.g. from cloud or custom path)',
    icon: '📁',
    bestFor: 'GKE, EKS, AKS, or when the app can read a file path',
  },
  {
    id: 'context',
    title: 'Use default kubeconfig',
    subtitle: 'kubectl already works; use my current context',
    icon: '⎈',
    bestFor: 'Local dev when the backend can read ~/.kube/config',
  },
  {
    id: 'in_cluster',
    title: 'In-cluster',
    subtitle: 'KubeMemory runs inside the cluster (e.g. as a pod)',
    icon: '🔧',
    bestFor: 'Production when KubeMemory is deployed in the same cluster',
  },
]

const PASTE_INSTRUCTIONS = [
  'In your terminal (where kubectl works), run:',
  'kubectl config view --minify --raw',
  'Copy the entire output, then paste it in the box below.',
  'If this app runs in Docker: check "App runs in Docker". Connection refused? Use "Use Kind network" (no need to recreate the cluster).',
]

const FILE_PATH_INSTRUCTIONS = [
  'Use the path to your kubeconfig file that this app can read.',
  'Examples: ~/.kube/config, /path/to/my-cluster.yaml, or a path mounted into the app container.',
  'If the app runs in Docker, the path must be inside the container (e.g. a mounted volume).',
]

const CONTEXT_INSTRUCTIONS = [
  'Run: kubectl config current-context',
  'Enter that context name below (e.g. kind-demo, minikube, or my-gke-context).',
  'The app will use the default kubeconfig from the environment.',
]

const IN_CLUSTER_INSTRUCTIONS = [
  'No kubeconfig needed. Use this when KubeMemory is deployed as a pod in the same cluster.',
  'The app will use the in-cluster service account.',
]

export default function ClusterConnect() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [method, setMethod] = useState('')
  const [clusterName, setClusterName] = useState('')
  const [kubeconfigPath, setKubeconfigPath] = useState('~/.kube/config')
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
  const [useKindNetwork, setUseKindNetwork] = useState(false)
  const [kindClusterName, setKindClusterName] = useState('')
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

  const getMethodInstructions = () => {
    if (method === 'paste') return PASTE_INSTRUCTIONS
    if (method === 'kubeconfig') return FILE_PATH_INSTRUCTIONS
    if (method === 'context') return CONTEXT_INSTRUCTIONS
    if (method === 'in_cluster') return IN_CLUSTER_INSTRUCTIONS
    return []
  }

  const canProceedFromStep2 = () => {
    if (!method) return false
    if (method === 'paste') return !!kubeconfigPaste.trim()
    if (method === 'in_cluster') return !!clusterName.trim()
    return true
  }

  const getDefaultClusterName = () => {
    if (clusterName) return clusterName
    if (method === 'paste') return 'my-cluster'
    if (method === 'context') return 'kind-demo'
    return 'my-cluster'
  }

  const handleNextFromMethod = () => {
    if (!method || !canProceedFromStep2()) return
    const path = method === 'in_cluster' ? '' : (method === 'paste' ? '' : (kubeconfigPath || '~/.kube/config'))
    const ctx = method === 'context' ? (contextName || `kind-${clusterName || 'demo'}`) : (contextName || '')
    const name = (clusterName || '').trim() || getDefaultClusterName()
    const payload = {
      name,
      connection_method: method === 'in_cluster' ? 'in_cluster' : method === 'context' ? 'context' : 'kubeconfig',
      kubeconfig_path: path,
      context_name: ctx,
      namespaces: [],
    }
    if (method === 'paste') {
      payload.kubeconfig_content = kubeconfigPaste.trim()
      payload.use_docker_host = useDockerHost && !useKindNetwork
      payload.use_kind_network = useKindNetwork
      if (useKindNetwork && kindClusterName.trim()) payload.kind_cluster_name = kindClusterName.trim()
    }
    createCluster(payload)
      .then((c) => {
        setClusterId(c.id)
        setClusterName(name)
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
        {/* Step 1: Welcome */}
        {step === 1 && (
          <>
            <h1 className="text-xl font-mono font-bold text-white">⎈ Connect a cluster</h1>
            <p className="text-muted text-sm">
              Choose how you want to connect. KubeMemory only needs read-only access and never modifies your cluster.
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
              Choose how to connect →
            </button>
          </>
        )}

        {/* Step 2: Pick workflow + configure */}
        {step === 2 && (
          <>
            <h2 className="font-mono font-semibold text-white">How do you want to connect?</h2>
            <p className="text-muted text-xs">
              Not sure? Use <strong className="text-white">Paste kubeconfig</strong> if you can run <code className="bg-surface2 px-1 rounded">kubectl</code> on your machine.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {WORKFLOWS.map((m) => (
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
                  <span className="font-mono text-sm font-medium block">{m.title}</span>
                  <span className="text-xs mt-0.5 block opacity-90">{m.subtitle}</span>
                  <span className="text-xs mt-2 block opacity-75">Best for: {m.bestFor}</span>
                </button>
              ))}
            </div>

            {method && (
              <div className="rounded-lg border border-border bg-surface2 p-4 space-y-4">
                <p className="text-xs font-mono text-accent uppercase tracking-wider">Do this:</p>
                <ul className="text-sm text-muted space-y-1 list-decimal list-inside">
                  {getMethodInstructions().map((line, i) => (
                    <li key={i}>
                      {line.startsWith('kubectl') ? (
                        <code className="bg-bg px-1.5 py-0.5 rounded text-white text-xs">{line}</code>
                      ) : (
                        line
                      )}
                    </li>
                  ))}
                </ul>

                <div>
                  <label className="block text-xs font-mono text-muted mb-1">Cluster name (for display)</label>
                  <input
                    type="text"
                    value={clusterName}
                    onChange={(e) => setClusterName(e.target.value)}
                    className="w-full rounded border border-border bg-surface px-3 py-2 text-white font-mono text-sm"
                    placeholder={method === 'context' ? 'e.g. kind-demo' : 'e.g. my-cluster'}
                  />
                </div>

                {method === 'paste' && (
                  <>
                    <div>
                      <label className="block text-xs font-mono text-muted mb-1">Paste kubeconfig YAML here</label>
                      <textarea
                        value={kubeconfigPaste}
                        onChange={(e) => setKubeconfigPaste(e.target.value)}
                        placeholder="Paste the output of kubectl config view --minify --raw"
                        rows={6}
                        className="w-full rounded border border-border bg-surface px-3 py-2 text-white font-mono text-xs"
                      />
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={useDockerHost}
                        onChange={(e) => setUseDockerHost(e.target.checked)}
                        className="rounded border-border"
                      />
                      <span className="text-sm text-muted">App runs in Docker (cluster is on the same machine)</span>
                    </label>
                    {useDockerHost && (
                      <div className="rounded border border-border bg-surface p-3 space-y-2">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={useKindNetwork}
                            onChange={(e) => setUseKindNetwork(e.target.checked)}
                            className="rounded border-border"
                          />
                          <span className="text-sm text-accent font-medium">Use Kind network (cluster already on 127.0.0.1? No need to recreate)</span>
                        </label>
                        <p className="text-xs text-muted">
                          Connects via Kind&apos;s Docker network to the control-plane container. Backend must be on that network: run once <code className="bg-bg px-1 rounded">docker network connect kind $(docker compose ps -q django-api)</code>, or start the app with <code className="bg-bg px-1 rounded">docker compose -f docker-compose.yml -f docker-compose.kind.yml up -d</code> (after creating your Kind cluster).
                        </p>
                        {useKindNetwork && (
                          <div>
                            <label className="block text-xs font-mono text-muted mb-1">Kind cluster name (optional)</label>
                            <input
                              type="text"
                              value={kindClusterName}
                              onChange={(e) => setKindClusterName(e.target.value)}
                              className="w-full rounded border border-border bg-surface px-3 py-2 text-white font-mono text-sm"
                              placeholder="e.g. demo — leave blank to infer from kubeconfig"
                            />
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}

                {method === 'kubeconfig' && (
                  <>
                    <div>
                      <label className="block text-xs font-mono text-muted mb-1">Path to kubeconfig file</label>
                      <input
                        type="text"
                        value={kubeconfigPath}
                        onChange={(e) => setKubeconfigPath(e.target.value)}
                        className="w-full rounded border border-border bg-surface px-3 py-2 text-white font-mono text-sm"
                        placeholder="~/.kube/config or /path/to/config"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-mono text-muted mb-1">Context name (optional)</label>
                      <input
                        type="text"
                        value={contextName}
                        onChange={(e) => setContextName(e.target.value)}
                        className="w-full rounded border border-border bg-surface px-3 py-2 text-white font-mono text-sm"
                        placeholder="Leave blank for current context"
                      />
                    </div>
                  </>
                )}

                {method === 'context' && (
                  <div>
                    <label className="block text-xs font-mono text-muted mb-1">Context name (from kubectl config current-context)</label>
                    <input
                      type="text"
                      value={contextName}
                      onChange={(e) => setContextName(e.target.value)}
                      className="w-full rounded border border-border bg-surface px-3 py-2 text-white font-mono text-sm"
                      placeholder="e.g. kind-demo, minikube"
                    />
                  </div>
                )}
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
                disabled={!canProceedFromStep2()}
                className="px-4 py-2 rounded bg-accent text-bg font-mono font-semibold hover:opacity-90 disabled:opacity-50"
              >
                Save & test connection →
              </button>
            </div>
          </>
        )}

        {/* Step 3: Test */}
        {step === 3 && (
          <>
            <h2 className="font-mono font-semibold text-white">Test connection</h2>
            <p className="text-muted text-sm">
              Cluster &quot;{clusterName || 'my-cluster'}&quot; is configured. Verify we can reach it.
            </p>
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testing || !clusterId}
              className="px-4 py-2 rounded border border-accent text-accent font-mono text-sm hover:bg-accent/10 disabled:opacity-50"
            >
              {testing ? 'Testing…' : 'Test connection'}
            </button>
            {testError && (
              <div className="rounded border border-red-500/50 bg-red-500/10 p-4 text-sm space-y-3">
                <p className="font-mono text-red-400 font-semibold">✗ Connection failed</p>
                <p className="text-muted mt-1">{testError}</p>
                <p className="text-xs text-muted font-medium">What to try:</p>
                <ul className="list-disc list-inside text-xs text-muted space-y-0.5">
                  <li>Cluster running? Run <code className="bg-bg px-1 rounded">kubectl get nodes</code> or <code className="bg-bg px-1 rounded">kind get clusters</code></li>
                  <li>Correct context? <code className="bg-bg px-1 rounded">kubectl config current-context</code></li>
                  <li>App in Docker + connection refused? Go back → Paste kubeconfig → check <strong className="text-white">Use Kind network</strong>, then attach backend to Kind network: <code className="bg-bg px-1 rounded block mt-1">docker network connect kind $(docker compose ps -q django-api)</code> or use <code className="bg-bg px-1 rounded">docker compose -f docker-compose.yml -f docker-compose.kind.yml up -d</code></li>
                  <li>Otherwise: use &quot;App runs in Docker&quot; (cluster API must be on 0.0.0.0) or run the app on the host</li>
                </ul>
              </div>
            )}
            {testResult?.connected && (
              <div className="rounded border border-accent/50 bg-accent/10 p-4 text-sm">
                <p className="font-mono text-accent font-semibold">✓ Connected</p>
                <p className="text-muted mt-1">
                  {testResult.node_count} nodes · K8s {testResult.server_version || 'unknown'}
                </p>
              </div>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="px-3 py-1.5 rounded border border-border text-muted font-mono text-sm"
              >
                ← Back
              </button>
              <button
                type="button"
                onClick={handleNextFromTest}
                disabled={!testResult?.connected}
                className="px-4 py-2 rounded bg-accent text-bg font-mono font-semibold hover:opacity-90 disabled:opacity-50"
              >
                Choose namespaces →
              </button>
            </div>
          </>
        )}

        {/* Step 4: Namespaces + Start */}
        {step === 4 && (
          <>
            <h2 className="font-mono font-semibold text-white">Which namespaces to watch?</h2>
            <p className="text-muted text-sm">We’ll only read events from these. Avoid kube-system (noisy).</p>
            {loadingNamespaces ? (
              <p className="text-muted">Loading…</p>
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
                    <span className="font-mono text-sm text-white">{ns}</span>
                    {ns === 'kube-system' && <span className="text-xs text-muted">(not recommended)</span>}
                  </label>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(3)}
                className="px-3 py-1.5 rounded border border-border text-muted font-mono text-sm"
              >
                ← Back
              </button>
              <button
                type="button"
                onClick={handleStartWatching}
                disabled={connecting || selectedNamespaces.length === 0}
                className="px-4 py-2 rounded bg-accent text-bg font-mono font-semibold hover:opacity-90 disabled:opacity-50"
              >
                {connecting ? 'Connecting…' : 'Start watching'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
