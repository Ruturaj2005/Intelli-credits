/**
 * Pipeline — live view of the 4-agent appraisal pipeline with WebSocket + polling.
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import axios from 'axios'
import AgentBlock from '../components/AgentBlock.jsx'
import TerminalLog from '../components/TerminalLog.jsx'

const API = '/api'
const AGENT_ORDER = ['ingestor', 'research', 'scorer', 'cam_generator']

function ElapsedTimer({ startedAt }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!startedAt) return
    const start = new Date(startedAt).getTime()
    const tick = () => setElapsed(Math.floor((Date.now() - start) / 1000))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [startedAt])

  const mins = Math.floor(elapsed / 60)
  const secs = elapsed % 60
  return (
    <span className="font-mono text-[#00d4aa]">
      {String(mins).padStart(2, '0')}:{String(secs).padStart(2, '0')}
    </span>
  )
}

export default function Pipeline() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const wsRef = useRef(null)
  const pollRef = useRef(null)

  const [status, setStatus] = useState('QUEUED')
  const [agentStatuses, setAgentStatuses] = useState({
    ingestor: 'PENDING',
    research: 'PENDING',
    scorer: 'PENDING',
    cam_generator: 'PENDING',
  })
  const [logs, setLogs] = useState([])
  const [startedAt, setStartedAt] = useState(null)
  const [conflictDetected, setConflictDetected] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  const applyUpdate = (payload) => {
    if (payload.status) setStatus(payload.status)
    if (payload.agent_statuses) setAgentStatuses(payload.agent_statuses)
    if (payload.conflict_detected !== undefined) setConflictDetected(payload.conflict_detected)
    if (payload.logs) {
      setLogs((prev) => {
        // Merge: keep unique by index
        const combined = [...payload.logs]
        return combined.length > prev.length ? combined : prev
      })
    }
  }

  // WebSocket connection
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const wsUrl = `${protocol}://${window.location.host}/ws/${jobId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'snapshot' || msg.type === 'update') {
          applyUpdate(msg.payload)
        } else if (msg.type === 'complete') {
          setStatus('COMPLETED')
          setTimeout(() => navigate(`/appraisal/${jobId}/results`), 1500)
        } else if (msg.type === 'error') {
          setStatus('FAILED')
          setErrorMsg(msg.payload?.message || 'Unknown error')
        }
      } catch {
        // ignore parse errors
      }
    }

    ws.onerror = () => {
      // Fall through to polling
    }

    return () => {
      ws.close()
    }
  }, [jobId, navigate])

  // Polling fallback (every 2s)
  useEffect(() => {
    const poll = async () => {
      try {
        const { data } = await axios.get(`${API}/appraisal/${jobId}/status`)
        applyUpdate({
          status: data.status,
          agent_statuses: data.agent_statuses,
          logs: data.logs,
          conflict_detected: data.conflict_detected,
        })
        if (!startedAt && data.started_at) setStartedAt(data.started_at)

        if (data.status === 'COMPLETED') {
          clearInterval(pollRef.current)
          setTimeout(() => navigate(`/appraisal/${jobId}/results`), 1500)
        } else if (data.status === 'FAILED') {
          clearInterval(pollRef.current)
          setErrorMsg(data.error_message || 'Pipeline failed.')
        }
      } catch {
        // Keep polling
      }
    }

    poll()
    pollRef.current = setInterval(poll, 2000)
    return () => clearInterval(pollRef.current)
  }, [jobId, navigate, startedAt])

  const isComplete = status === 'COMPLETED'
  const isFailed = status === 'FAILED'

  return (
    <div className="max-w-6xl mx-auto px-8 py-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-syne font-bold text-2xl text-[#e8f0f5]">Appraisal Pipeline</h1>
          <p className="text-[#4a6070] text-sm mt-1 font-mono">Job: {jobId}</p>
        </div>
        <div className="flex items-center gap-4">
          {startedAt && !isComplete && !isFailed && (
            <div className="card px-4 py-2 flex items-center gap-2">
              <span className="text-[11px] text-[#4a6070]">Elapsed:</span>
              <ElapsedTimer startedAt={startedAt} />
            </div>
          )}
          <div className={`badge ${
            isComplete ? 'badge-approve' :
            isFailed ? 'badge-reject' :
            status === 'RUNNING' ? 'badge-running' : 'badge-pending'
          }`}>
            {isComplete ? '✓ Complete' : isFailed ? '✗ Failed' : status === 'RUNNING' ? '⚡ Running' : status}
          </div>
        </div>
      </div>

      {/* Conflict Banner */}
      {conflictDetected && (
        <div className="mb-6 rounded-xl border border-[#ef476f]/40 bg-[#ef476f]/8 px-6 py-4 flex items-start gap-3 animate-slide-up">
          <span className="text-xl">⚡</span>
          <div>
            <p className="font-syne font-bold text-[#ef476f] text-sm">CONFLICT DETECTED</p>
            <p className="text-xs text-[#4a6070] mt-1">
              Ingestor financials and Research findings contradict each other.
              The Arbitrator Agent is reconciling conflicting signals before final scoring.
            </p>
          </div>
        </div>
      )}

      {/* Agent Pipeline */}
      <div className="card p-6 mb-6">
        <h2 className="font-syne font-semibold text-[#e8f0f5] mb-6 text-sm uppercase tracking-wider text-[#4a6070]">
          Agent Pipeline
        </h2>
        <div className="flex items-start overflow-x-auto gap-0 pb-2">
          {AGENT_ORDER.map((key, i) => (
            <AgentBlock
              key={key}
              agentKey={key}
              status={agentStatuses[key] || 'PENDING'}
              isLast={i === AGENT_ORDER.length - 1}
            />
          ))}
        </div>
      </div>

      {/* Terminal */}
      <TerminalLog logs={logs} maxHeight={360} title="Live Agent Log" />

      {/* Error */}
      {isFailed && errorMsg && (
        <div className="mt-4 rounded-xl border border-[#ef476f]/30 bg-[#ef476f]/10 px-5 py-4">
          <p className="text-sm text-[#ef476f]">⚠ Pipeline failed: {errorMsg}</p>
          <button
            onClick={() => navigate('/appraisal/new')}
            className="btn-secondary mt-3 text-xs py-2"
          >
            Start New Appraisal
          </button>
        </div>
      )}

      {/* Success redirect notice */}
      {isComplete && (
        <div className="mt-6 rounded-xl border border-[#00d4aa]/30 bg-[#00d4aa]/5 px-6 py-4 flex items-center justify-between animate-slide-up">
          <div>
            <p className="font-syne font-bold text-[#00d4aa]">✓ Appraisal Complete</p>
            <p className="text-xs text-[#4a6070] mt-1">Redirecting to results...</p>
          </div>
          <button
            onClick={() => navigate(`/appraisal/${jobId}/results`)}
            className="btn-primary text-sm py-2.5 px-6"
          >
            View Results →
          </button>
        </div>
      )}
    </div>
  )
}
