/**
 * Dashboard — KPI summary + recent applications table + agent activity feed.
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

const API = '/api'

function KpiCard({ label, value, sub, accent }) {
  return (
    <div className="card p-5 flex flex-col gap-1 hover:glow-accent transition-all">
      <p className="text-[11px] text-[#4a6070] uppercase tracking-widest font-mono">{label}</p>
      <p
        className="font-syne font-bold text-3xl num"
        style={{ color: accent || '#e8f0f5' }}
      >
        {value ?? '—'}
      </p>
      {sub && <p className="text-xs text-[#4a6070]">{sub}</p>}
    </div>
  )
}

function StatusBadge({ status, recommendation }) {
  if (status === 'RUNNING') return <span className="badge badge-running">Running</span>
  if (status === 'FAILED') return <span className="badge badge-reject">Failed</span>
  if (status === 'QUEUED') return <span className="badge badge-pending">Queued</span>
  if (!recommendation) return <span className="badge badge-pending">{status}</span>
  if (recommendation.includes('REJECT')) return <span className="badge badge-reject">Rejected</span>
  if (recommendation.includes('CONDITIONAL')) return <span className="badge badge-conditional">Conditional</span>
  return <span className="badge badge-approve">Approved</span>
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [summary, setSummary] = useState(null)
  const [recentActivity, setRecentActivity] = useState([])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const { data } = await axios.get(`${API}/dashboard/summary`)
        setSummary(data)
        setRecentActivity(data.recent_applications || [])
      } catch {
        // If backend not reachable, show placeholder
        setSummary({ cases_today: 0, avg_turnaround_min: 0, approval_rate_pct: 0, pending_reviews: 0 })
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 15000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="max-w-7xl mx-auto px-8 py-8 animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-syne font-bold text-2xl text-[#e8f0f5]">Credit Appraisal Dashboard</h1>
        <p className="text-[#4a6070] text-sm mt-1">
          AI-powered corporate lending intelligence for Indian banks
        </p>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <KpiCard
          label="Cases Today"
          value={summary?.cases_today ?? '—'}
          accent="#00d4aa"
        />
        <KpiCard
          label="Avg Turnaround"
          value={summary?.avg_turnaround_min ? `${summary.avg_turnaround_min}m` : '—'}
          sub="vs 10–15 business days"
          accent="#0099ff"
        />
        <KpiCard
          label="Approval Rate"
          value={summary?.approval_rate_pct != null ? `${summary.approval_rate_pct}%` : '—'}
          accent="#00d4aa"
        />
        <KpiCard
          label="Pending Reviews"
          value={summary?.pending_reviews ?? '—'}
          accent="#ffd166"
        />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Recent Applications Table */}
        <div className="col-span-2 card overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-[#1a2530]">
            <h2 className="font-syne font-semibold text-[#e8f0f5]">Recent Applications</h2>
            <button
              onClick={() => navigate('/appraisal/new')}
              className="btn-primary text-xs py-2 px-4"
            >
              + New Appraisal
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#1a2530]">
                  {['Company', 'Sector', 'Score', 'Decision', 'Turnaround', 'Status'].map((h) => (
                    <th
                      key={h}
                      className="text-left px-6 py-3 text-[10px] uppercase tracking-widest text-[#4a6070] font-mono"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recentActivity.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-[#4a6070] text-sm">
                      No appraisals yet. Start your first one →
                    </td>
                  </tr>
                ) : (
                  recentActivity.map((job) => (
                    <tr
                      key={job.job_id}
                      className="border-b border-[#1a2530]/50 hover:bg-[#111820] cursor-pointer transition-colors"
                      onClick={() =>
                        job.status === 'COMPLETED'
                          ? navigate(`/appraisal/${job.job_id}/results`)
                          : navigate(`/appraisal/${job.job_id}/pipeline`)
                      }
                    >
                      <td className="px-6 py-3.5">
                        <span className="text-sm font-medium text-[#e8f0f5]">
                          {job.company_name || '—'}
                        </span>
                      </td>
                      <td className="px-6 py-3.5">
                        <span className="text-xs text-[#4a6070]">{job.sector || '—'}</span>
                      </td>
                      <td className="px-6 py-3.5">
                        <span className="num text-sm font-mono text-[#e8f0f5]">
                          {job.weighted_score ? `${Number(job.weighted_score).toFixed(1)}` : '—'}
                        </span>
                      </td>
                      <td className="px-6 py-3.5">
                        <StatusBadge status={job.status} recommendation={job.recommendation} />
                      </td>
                      <td className="px-6 py-3.5">
                        <span className="num text-xs text-[#4a6070] font-mono">
                          {job.turnaround || '—'}
                        </span>
                      </td>
                      <td className="px-6 py-3.5">
                        <StatusBadge status={job.status} />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Agent Activity Feed */}
        <div className="card p-5">
          <h2 className="font-syne font-semibold text-[#e8f0f5] mb-4">Agent Activity</h2>
          {recentActivity.length === 0 ? (
            <p className="text-[#4a6070] text-xs text-center py-8">
              No recent activity.
            </p>
          ) : (
            <ul className="space-y-3">
              {recentActivity
                .filter((j) => j.status === 'RUNNING' || j.status === 'COMPLETED')
                .slice(0, 5)
                .map((job) => (
                  <li
                    key={job.job_id}
                    className="flex items-start gap-3 cursor-pointer"
                    onClick={() => navigate(`/appraisal/${job.job_id}/pipeline`)}
                  >
                    <div
                      className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                        job.status === 'RUNNING' ? 'bg-[#0099ff] animate-pulse' : 'bg-[#00d4aa]'
                      }`}
                    />
                    <div>
                      <p className="text-xs font-medium text-[#e8f0f5]">{job.company_name}</p>
                      <p className="text-[11px] text-[#4a6070]">
                        {job.status === 'RUNNING' ? 'Pipeline running...' : `Completed · ${job.turnaround || ''}`}
                      </p>
                    </div>
                  </li>
                ))}
            </ul>
          )}

          {/* Quick-launch */}
          <div className="mt-6 pt-4 border-t border-[#1a2530]">
            <button
              onClick={() => navigate('/appraisal/new')}
              className="w-full btn-primary text-xs py-2.5"
            >
              Run New Appraisal
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
