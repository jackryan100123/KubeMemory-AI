import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { formatDistanceToNow, format } from 'date-fns'
import { useIncident } from '../hooks/useIncidents'
import { useAnalysis } from '../hooks/useAnalysis'
import { useSubmitFix } from '../hooks/useIncidents'
import { updateIncidentStatus } from '../api/incidents'
import { triggerAnalyze, generateRunbook } from '../api/agents'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { marked } from 'marked'
import SeverityBadge from '../components/incidents/SeverityBadge'
import StatusDot from '../components/incidents/StatusDot'
import LoadingSpinner from '../components/shared/LoadingSpinner'
import SkeletonLoader from '../components/shared/SkeletonLoader'
import ErrorBoundary from '../components/shared/ErrorBoundary'

const STATUS_OPTIONS = [
  { value: 'open', label: 'Open' },
  { value: 'investigating', label: 'Investigating' },
  { value: 'resolved', label: 'Resolved' },
]

export default function IncidentDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: incident, isLoading: incidentLoading, error: incidentError } = useIncident(id)
  const { data: analysisData } = useAnalysis(id)
  const submitFixMutation = useSubmitFix(id)

  const [statusMenuOpen, setStatusMenuOpen] = useState(false)
  const [logsExpanded, setLogsExpanded] = useState(false)
  const [fixDescription, setFixDescription] = useState('')
  const [fixAppliedBy, setFixAppliedBy] = useState('')
  const [fixWorked, setFixWorked] = useState(true)
  const [aiWasWrong, setAiWasWrong] = useState(false)
  const [correctionOfId, setCorrectionOfId] = useState('')
  const [triggeringAnalysis, setTriggeringAnalysis] = useState(false)
  const [runbookMd, setRunbookMd] = useState(null)
  const [runbookLoading, setRunbookLoading] = useState(false)
  const [runbookModalOpen, setRunbookModalOpen] = useState(false)

  const analysis = analysisData?.status === 'ok' ? analysisData : null
  const analysisPending = !incident?.ai_analysis?.trim() && analysisData?.status !== 'ok'
  const aiSuggestedFixes = incident?.fixes?.filter((f) => f.ai_suggested) ?? []

  const handleRunAnalysis = async () => {
    if (!id || triggeringAnalysis) return
    setTriggeringAnalysis(true)
    try {
      const result = await triggerAnalyze(id)
      if (result.status === 'error') {
        toast.error(result.error || 'Analysis failed')
      } else {
        toast.success(result.status === 'ok' ? 'Analysis complete.' : 'Analysis queued.')
      }
      queryClient.invalidateQueries(['incident', id])
      queryClient.invalidateQueries(['analysis', id])
    } catch (err) {
      toast.error(err.response?.data?.error || err.message || 'Failed to run analysis')
    } finally {
      setTriggeringAnalysis(false)
    }
  }

  const handleGenerateRunbook = () => {
    if (!id || runbookLoading) return
    setRunbookLoading(true)
    setRunbookMd(null)
    generateRunbook(id)
      .then((res) => {
        setRunbookMd(res.runbook_md || '')
        setRunbookModalOpen(true)
      })
      .catch((e) => toast.error(e.response?.data?.error || e.message || 'Runbook generation failed'))
      .finally(() => setRunbookLoading(false))
  }

  const handleCopyRunbook = () => {
    if (runbookMd) {
      navigator.clipboard.writeText(runbookMd)
      toast.success('Copied to clipboard')
    }
  }

  const handleDownloadRunbook = () => {
    if (!runbookMd || !incident) return
    const slug = (incident.service_name || incident.pod_name || 'incident').replace(/\s+/g, '-')
    const dateStr = format(new Date(incident.occurred_at || Date.now()), 'yyyy-MM-dd')
    const filename = `runbook-${slug}-${dateStr}.md`
    const blob = new Blob([runbookMd], { type: 'text/markdown' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
    URL.revokeObjectURL(a.href)
    toast.success('Downloaded')
  }

  const handleStatusChange = async (newStatus) => {
    setStatusMenuOpen(false)
    try {
      await updateIncidentStatus(id, newStatus)
      queryClient.invalidateQueries(['incident', id])
    } catch (e) {
      console.error(e)
    }
  }

  const handleSubmitFix = (e) => {
    e.preventDefault()
    if (!fixDescription.trim() || !fixAppliedBy.trim()) return
    submitFixMutation.mutate(
      {
        description: fixDescription.trim(),
        applied_by: fixAppliedBy.trim(),
        worked: fixWorked,
        ai_suggested: false,
        ...(aiWasWrong && correctionOfId ? { correction_of: Number(correctionOfId) } : {}),
      },
      {
        onSuccess: () => {
          setFixDescription('')
          setFixAppliedBy('')
          setFixWorked(true)
          setAiWasWrong(false)
          setCorrectionOfId('')
        },
      }
    )
  }

  if (incidentError || (!incidentLoading && !incident)) {
    return (
      <div className="p-6">
        <p className="text-accent-red">Incident not found.</p>
        <button
          type="button"
          onClick={() => navigate('/')}
          className="mt-2 text-accent hover:underline font-mono"
        >
          ← Back to Dashboard
        </button>
      </div>
    )
  }

  if (incidentLoading && !incident) {
    return (
      <div className="flex justify-center items-center min-h-[300px]">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className="p-6 flex flex-col lg:flex-row gap-6">
        {/* Left panel — 65% */}
        <div className="lg:w-[65%] space-y-6">
          {/* Header */}
          <div className="rounded-lg border border-border bg-surface p-4">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={incident.severity} />
            <span className="font-mono text-lg text-white">{incident.incident_type}</span>
            {Number(incident.estimated_waste_usd) > 0 && (
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-yellow-500/20 text-yellow-400">
                💸 ~${Math.round(Number(incident.estimated_waste_usd) / 10) * 10}/month if unresolved
              </span>
            )}
          </div>
            <p className="font-mono text-sm text-muted mt-1">
              {incident.pod_name} / {incident.namespace} / {incident.node_name || '—'}
            </p>
            <p className="text-xs text-muted mt-2">
              Occurred: {incident.occurred_at ? formatDistanceToNow(new Date(incident.occurred_at), { addSuffix: true }) : '—'} | Status:{' '}
              <StatusDot status={incident.status} /> {incident.status}
              <span className="ml-2 relative inline-block">
                <button
                  type="button"
                  onClick={() => setStatusMenuOpen(!statusMenuOpen)}
                  className="text-accent font-mono text-xs hover:underline"
                >
                  Change Status ▾
                </button>
                {statusMenuOpen && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setStatusMenuOpen(false)} aria-hidden />
                    <ul className="absolute left-0 top-full mt-1 py-1 rounded border border-border bg-surface2 z-20 min-w-[140px]">
                      {STATUS_OPTIONS.map((opt) => (
                        <li key={opt.value}>
                          <button
                            type="button"
                            onClick={() => handleStatusChange(opt.value)}
                            className="w-full text-left px-3 py-2 text-sm font-mono text-white hover:bg-surface"
                          >
                            {opt.label}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </span>
            </p>
          </div>

          {/* AI Analysis */}
          <div className="rounded-lg border border-border bg-surface overflow-hidden">
            <div className="px-4 py-3 border-b border-border flex items-center justify-between flex-wrap gap-2">
              <span className="font-mono font-semibold text-white">🧠 AI ANALYSIS</span>
              <div className="flex items-center gap-2">
                {analysis && (
                  <span className="text-xs font-mono text-muted">
                    Confidence: {Math.round((analysis.confidence || 0) * 100)}%
                  </span>
                )}
                {analysisPending && (
                  <button
                    type="button"
                    onClick={handleRunAnalysis}
                    disabled={triggeringAnalysis}
                    className="px-3 py-1.5 rounded bg-accent text-bg font-mono text-xs font-semibold hover:opacity-90 disabled:opacity-50"
                  >
                    {triggeringAnalysis ? 'Running… (1–2 min)' : 'Run AI analysis'}
                  </button>
                )}
              </div>
            </div>
            <div className="p-4 font-sans text-sm text-muted">
              {analysisPending ? (
                <div className="space-y-3">
                  <p className="text-accent animate-pulse">
                    {triggeringAnalysis ? 'Running analysis…' : 'Analyzing...'}
                  </p>
                  <p className="text-xs text-muted">
                    Click “Run AI analysis” above to generate recommendations (requires Ollama). May take 1–2 minutes.
                  </p>
                  <SkeletonLoader lines={4} />
                </div>
              ) : analysis || incident.ai_analysis ? (
                <div className="space-y-4 text-white/90">
                  {analysis?.root_cause && (
                    <section>
                      <h4 className="font-mono text-accent text-xs uppercase mb-1">ROOT CAUSE</h4>
                      <p className="whitespace-pre-wrap">{analysis.root_cause}</p>
                    </section>
                  )}
                  {(analysis?.recommendation || incident.ai_analysis) && (
                    <section>
                      <h4 className="font-mono text-accent text-xs uppercase mb-1">RECOMMENDATION</h4>
                      <p className="whitespace-pre-wrap">{analysis?.recommendation || incident.ai_analysis}</p>
                    </section>
                  )}
                  {analysis?.prevention_advice && (
                    <section>
                      <h4 className="font-mono text-accent text-xs uppercase mb-1">PREVENTION</h4>
                      <p className="whitespace-pre-wrap">{analysis.prevention_advice}</p>
                    </section>
                  )}
                  {(analysis?.sources?.length > 0) && (
                    <section>
                      <h4 className="font-mono text-accent text-xs uppercase mb-1">GROUNDED IN</h4>
                      <ul className="list-disc list-inside space-y-1">
                        {analysis.sources.map((s, i) => (
                          <li key={i} className="font-mono text-xs">{s}</li>
                        ))}
                      </ul>
                    </section>
                  )}
                  {(analysis || incident.ai_analysis) && (
                    <div className="mt-4 p-4 rounded border border-border bg-surface2">
                      <p className="font-mono text-accent text-xs uppercase mb-2">📋 GENERATE RUNBOOK</p>
                      <p className="text-muted text-sm mb-3">
                        Create a reusable runbook from this incident + cluster history
                      </p>
                      <button
                        type="button"
                        onClick={handleGenerateRunbook}
                        disabled={runbookLoading}
                        className="px-4 py-2 rounded bg-accent text-bg font-mono text-sm font-semibold hover:opacity-90 disabled:opacity-50"
                      >
                        {runbookLoading ? 'Generating…' : 'GENERATE RUNBOOK'}
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-muted">No analysis available.</p>
                  <button
                    type="button"
                    onClick={handleRunAnalysis}
                    disabled={triggeringAnalysis}
                    className="px-3 py-2 rounded bg-accent text-bg font-mono text-sm font-semibold hover:opacity-90 disabled:opacity-50"
                  >
                    {triggeringAnalysis ? 'Running… (1–2 min)' : 'Run AI analysis'}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Raw Logs (collapsible) */}
          <div className="rounded-lg border border-border bg-surface overflow-hidden">
            <button
              type="button"
              onClick={() => setLogsExpanded(!logsExpanded)}
              className="w-full px-4 py-3 text-left font-mono text-sm text-white hover:bg-surface2 flex items-center gap-2"
            >
              {logsExpanded ? '▼' : '▶'} RAW LOGS
            </button>
            {logsExpanded && (
              <pre className="px-4 py-3 max-h-[300px] overflow-auto text-xs font-mono text-muted border-t border-border bg-bg">
                {incident.raw_logs || 'No raw logs.'}
              </pre>
            )}
          </div>
        </div>

        {/* Right panel — 35% */}
        <div className="lg:w-[35%] space-y-6">
          {/* Fix History */}
          <div className="rounded-lg border border-border bg-surface overflow-hidden">
            <div className="px-4 py-3 border-b border-border font-mono font-semibold text-white">
              FIX HISTORY
            </div>
            <div className="p-4 space-y-3">
              {!incident.fixes?.length ? (
                <p className="text-muted text-sm">No fixes recorded yet.</p>
              ) : (
                incident.fixes.map((fix) => (
                  <div key={fix.id} className="border-b border-border pb-3 last:border-0">
                    <p className="flex items-center gap-2 text-sm text-white">
                      {fix.worked ? '✓' : '✗'} {fix.description}
                    </p>
                    <p className="text-xs text-muted mt-1">
                      Applied by: {fix.applied_by} {fix.ai_suggested && '• AI suggested: Yes'}
                    </p>
                    {!fix.worked && <p className="text-xs text-muted">Didn&apos;t work</p>}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Submit Fix Form */}
          <form
            onSubmit={handleSubmitFix}
            className="rounded-lg border border-border bg-surface overflow-hidden"
          >
            <div className="px-4 py-3 border-b border-border font-mono font-semibold text-white">
              SUBMIT FIX
            </div>
            <div className="p-4 space-y-3">
              <div>
                <label className="block text-xs font-mono text-muted mb-1">What did you actually do?</label>
                <textarea
                  value={fixDescription}
                  onChange={(e) => setFixDescription(e.target.value)}
                  rows={3}
                  className="w-full rounded border border-border bg-surface2 px-3 py-2 text-sm text-white font-mono resize-y"
                  placeholder="Describe the fix..."
                />
              </div>
              <div>
                <label className="block text-xs font-mono text-muted mb-1">Applied by</label>
                <input
                  type="text"
                  value={fixAppliedBy}
                  onChange={(e) => setFixAppliedBy(e.target.value)}
                  className="w-full rounded border border-border bg-surface2 px-3 py-2 text-sm text-white font-mono"
                  placeholder="e.g. john@team.com"
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-white cursor-pointer">
                <input
                  type="checkbox"
                  checked={fixWorked}
                  onChange={(e) => setFixWorked(e.target.checked)}
                />
                This fix worked
              </label>
              <label className="flex items-start gap-2 text-sm text-white cursor-pointer">
                <input
                  type="checkbox"
                  checked={aiWasWrong}
                  onChange={(e) => setAiWasWrong(e.target.checked)}
                />
                <span>AI was wrong — this is the correct fix (enables Corrective RAG)</span>
              </label>
              {aiWasWrong && aiSuggestedFixes.length > 0 && (
                <div>
                  <label className="block text-xs font-mono text-muted mb-1">
                    Which of the AI&apos;s suggestions was incorrect?
                  </label>
                  <select
                    value={correctionOfId}
                    onChange={(e) => setCorrectionOfId(e.target.value)}
                    className="w-full rounded border border-border bg-surface2 px-3 py-2 text-sm text-white font-mono"
                  >
                    <option value="">Select...</option>
                    {aiSuggestedFixes.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.description?.slice(0, 60)}...
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <button
                type="submit"
                disabled={submitFixMutation.isPending || !fixDescription.trim() || !fixAppliedBy.trim()}
                className="w-full py-2 rounded bg-accent text-bg font-mono font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitFixMutation.isPending ? 'Submitting...' : 'SUBMIT FIX'}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Runbook Modal */}
      {runbookModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70" onClick={() => setRunbookModalOpen(false)}>
          <div className="bg-surface border border-border rounded-lg max-w-3xl w-full max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="px-4 py-3 border-b border-border flex items-center justify-between">
              <span className="font-mono font-semibold text-white">Generated Runbook</span>
              <button type="button" onClick={() => setRunbookModalOpen(false)} className="text-muted hover:text-white">✕</button>
            </div>
            <div className="p-4 overflow-auto flex-1 prose prose-invert prose-sm max-w-none">
              {runbookMd && (
                <div dangerouslySetInnerHTML={{ __html: marked.parse(runbookMd || '') }} />
              )}
            </div>
            <div className="px-4 py-3 border-t border-border flex gap-2">
              <button type="button" onClick={handleCopyRunbook} className="px-3 py-1.5 rounded border border-accent text-accent font-mono text-sm hover:bg-accent/10">
                📋 Copy Markdown
              </button>
              <button type="button" onClick={handleDownloadRunbook} className="px-3 py-1.5 rounded bg-accent text-bg font-mono text-sm hover:opacity-90">
                💾 Download .md
              </button>
            </div>
          </div>
        </div>
      )}
    </ErrorBoundary>
  )
}
