/**
 * Dashboard — KPI summary + recent applications table + agent activity feed.
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { TrendingUp, Clock, CheckCircle, AlertCircle, BarChart3, Activity } from 'lucide-react'

const API = '/api'

function KpiCard({ label, value, sub, accent, icon: Icon, trend }) {
  const [displayValue, setDisplayValue] = useState(0)
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    setIsLoaded(true)
    if (typeof value === 'number') {
      let current = 0
      const increment = value / 30
      const timer = setInterval(() => {
        current += increment
        if (current >= value) {
          setDisplayValue(value)
          clearInterval(timer)
        } else {
          setDisplayValue(Math.floor(current))
        }
      }, 20)
      return () => clearInterval(timer)
    }
  }, [value])

  return (
    <div className={`card card-interactive p-6 hover-lift group ${isLoaded ? 'animate-scale-in' : 'opacity-0'}`}>
      <div className="flex items-start justify-between mb-4">
        <div className="w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 group-hover:scale-110" 
             style={{ background: `${accent}15`, color: accent }}>
          <Icon size={24} strokeWidth={2.5} />
        </div>
        {trend && (
          <div className="flex items-center gap-1 text-xs font-mono" 
               style={{ color: trend > 0 ? 'var(--success)' : 'var(--danger)' }}>
            <TrendingUp size={12} className={trend < 0 ? 'rotate-180' : ''} />
            <span>{Math.abs(trend)}%</span>
          </div>
        )}
      </div>
      <p className="text-[11px] uppercase tracking-widest font-mono mb-2" 
         style={{ color: 'var(--muted-dark)' }}>
        {label}
      </p>
      <p className="font-syne font-bold text-5xl stat-counter mb-1" style={{ color: accent }}>
        {typeof value === 'number' ? displayValue : (value ?? '—')}
      </p>
      {sub && (
        <p className="text-xs mt-2 flex items-center gap-1" style={{ color: 'var(--muted)' }}>
          <span className="w-1 h-1 rounded-full bg-current opacity-50"></span>
          {sub}
        </p>
      )}
    </div>
  )
}

function StatusBadge({ status, recommendation }) {
  if (status === 'RUNNING') return <span className="badge badge-running animate-pulse">Running</span>
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
    <div className="max-w-7xl mx-auto px-8 py-10">
      {/* Animated Header */}
      <div className="mb-10 animate-slide-up">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-syne font-bold text-4xl mb-2" style={{ color: 'var(--text)' }}>
              Credit Appraisal Dashboard
            </h1>
            <p className="text-sm flex items-center gap-2" style={{ color: 'var(--muted)' }}>
              <Activity size={16} strokeWidth={2} />
              <span>AI-powered corporate lending intelligence • Real-time insights</span>
            </p>
          </div>
          <button
            onClick={() => navigate('/appraisal/new')}
            className="btn-primary flex items-center gap-2"
          >
            <span>Start New Appraisal</span>
            <span className="text-lg">→</span>
          </button>
        </div>
      </div>

      {/* Enhanced KPI Row */}
      <div className="grid grid-cols-4 gap-5 mb-10" style={{ animationDelay: '100ms' }}>
        <KpiCard
          label="Cases Today"
          value={summary?.cases_today ?? 0}
          icon={BarChart3}
          accent="var(--accent)"
          trend={12}
        />
        <KpiCard
          label="Avg Turnaround"
          value={summary?.avg_turnaround_min ? `${summary.avg_turnaround_min}m` : '—'}
          sub="vs 10–15 business days"
          icon={Clock}
          accent="var(--accent2)"
          trend={-23}
        />
        <KpiCard
          label="Approval Rate"
          value={summary?.approval_rate_pct != null ? `${summary.approval_rate_pct}%` : '—'}
          icon={CheckCircle}
          accent="var(--success)"
          trend={8}
        />
        <KpiCard
          label="Pending Reviews"
          value={summary?.pending_reviews ?? 0}
          icon={AlertCircle}
          accent="var(--warning)"
        />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Recent Applications Table */}
        <div className="col-span-2 card overflow-hidden animate-slide-up" style={{ animationDelay: '200ms' }}>
          <div className="flex items-center justify-between px-7 py-5 border-b" 
               style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
            <div>
              <h2 className="font-syne font-semibold text-lg" style={{ color: 'var(--text)' }}>
                Recent Applications
              </h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
                Last 10 submissions
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b" style={{ borderColor: 'var(--border)', background: 'var(--surface-elevated)' }}>
                  {['Company', 'Sector', 'Score', 'Decision', 'Time', 'Status'].map((h) => (
                    <th
                      key={h}
                      className="text-left px-6 py-3.5 text-[10px] uppercase tracking-widest font-mono font-semibold"
                      style={{ color: 'var(--muted-dark)' }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recentActivity.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-16 text-center">
                      <div className="flex flex-col items-center gap-3">
                        <div className="w-16 h-16 rounded-full flex items-center justify-center" 
                             style={{ background: 'var(--surface-elevated)' }}>
                          <BarChart3 size={28} style={{ color: 'var(--muted)' }} />
                        </div>
                        <p className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                          No appraisals yet
                        </p>
                        <p className="text-xs" style={{ color: 'var(--muted)' }}>
                          Start your first appraisal to see analytics here
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  recentActivity.map((job, idx) => (
                    <tr
                      key={job.job_id}
                      className="border-b cursor-pointer transition-all hover-lift"
                      style={{ 
                        borderColor: 'var(--border)',
                        animationDelay: `${300 + idx * 50}ms`
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'var(--surface-elevated)'
                        e.currentTarget.style.transform = 'scale(1.01)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent'
                        e.currentTarget.style.transform = 'scale(1)'
                      }}
                      onClick={() =>
                        job.status === 'COMPLETED'
                          ? navigate(`/appraisal/${job.job_id}/results`)
                          : navigate(`/appraisal/${job.job_id}/pipeline`)
                      }
                    >
                      <td className="px-6 py-4">
                        <span className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
                          {job.company_name || '—'}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-xs px-2 py-1 rounded-md font-mono" 
                              style={{ background: 'var(--surface-elevated)', color: 'var(--muted)' }}>
                          {job.sector || '—'}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="num text-sm font-mono font-bold" style={{ color: 'var(--accent)' }}>
                          {job.weighted_score ? `${Number(job.weighted_score).toFixed(1)}` : '—'}
                        </span>
                      </td>
                      <td className="px-6 py-3.5">
                        <StatusBadge status={job.status} recommendation={job.recommendation} />
                      </td>
                      <td className="px-6 py-3.5">
                        <span className="num text-xs font-mono" style={{ color: 'var(--muted)' }}>
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
          <h2 className="font-syne font-semibold mb-4" style={{ color: 'var(--text)' }}>
            Agent Activity
          </h2>
          {recentActivity.length === 0 ? (
            <p className="text-xs text-center py-8" style={{ color: 'var(--muted)' }}>
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
