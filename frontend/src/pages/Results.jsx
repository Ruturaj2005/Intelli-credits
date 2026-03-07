/**
 * Results — full Credit Appraisal results page with Five Cs radar,
 * financial metrics, red flags, decision reasoning, and CAM download.
 */
import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip,
  ResponsiveContainer, Cell,
} from 'recharts'
import FiveCsRadar from '../components/FiveCsRadar.jsx'
import RedFlagCard from '../components/RedFlagCard.jsx'

const API = '/api'

// ─── Helpers ────────────────────────────────────────────────────────────────

function fmt(v, dp = 2) {
  const n = Number(v)
  return isNaN(n) ? '—' : n.toFixed(dp)
}

function calcTurnaround(started, completed) {
  if (!started || !completed) return null
  try {
    const delta = (new Date(completed) - new Date(started)) / 1000
    const m = Math.floor(delta / 60)
    const s = Math.floor(delta % 60)
    return `${m}m ${s}s`
  } catch { return null }
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function DecisionBanner({ recommendation, loanAmount, interestRate }) {
  const rec = (recommendation || '').toUpperCase()
  const isApprove = rec === 'APPROVE'
  const isConditional = rec.includes('CONDITIONAL')
  const isReject = rec === 'REJECT'

  const config = isApprove
    ? { bg: 'bg-[#00d4aa]/10 border-[#00d4aa]/30', icon: '✅', color: 'text-[#00d4aa]', label: 'APPROVED' }
    : isConditional
    ? { bg: 'bg-[#ffd166]/10 border-[#ffd166]/30', icon: '⚠️', color: 'text-[#ffd166]', label: 'CONDITIONAL APPROVAL' }
    : { bg: 'bg-[#ef476f]/10 border-[#ef476f]/30', icon: '❌', color: 'text-[#ef476f]', label: 'REJECTED' }

  return (
    <div className={`w-full rounded-2xl border px-8 py-7 mb-8 ${config.bg} animate-slide-up`}>
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <span className="text-4xl">{config.icon}</span>
          <div>
            <p className="font-syne font-bold text-2xl" style={{ color: config.color.replace('text-', '') }}>
              {config.label}
            </p>
            {(isApprove || isConditional) && loanAmount ? (
              <p className="font-mono text-[#e8f0f5] mt-1">
                Rs. <span className="font-bold text-xl">{fmt(loanAmount)}</span> Crore
                {interestRate && <span className="text-[#4a6070]"> @ {interestRate}</span>}
              </p>
            ) : null}
          </div>
        </div>
        <div className="text-right">
          <p className="text-[11px] text-[#4a6070] uppercase tracking-wider">Credit Decision</p>
          <p className="text-[11px] text-[#4a6070] font-mono mt-0.5">Intelli-Credit AI Engine</p>
        </div>
      </div>
    </div>
  )
}

function MetricCard({ label, value, unit, sub, color }) {
  return (
    <div className="card p-4 text-center">
      <p className="text-[10px] text-[#4a6070] uppercase tracking-widest font-mono mb-1">{label}</p>
      <p className="font-mono font-bold text-2xl" style={{ color: color || '#e8f0f5' }}>
        {value ?? '—'}{unit && <span className="text-sm text-[#4a6070] ml-1">{unit}</span>}
      </p>
      {sub && <p className="text-[10px] text-[#4a6070] mt-1">{sub}</p>}
    </div>
  )
}

function ExplainerPopup({ c, data, show, onClose }) {
  if (!show) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60" />
      <div
        className="relative card p-6 max-w-md w-full animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-syne font-bold text-[#e8f0f5]">
            {c.toUpperCase()} — Score: {data?.score}/100
          </h3>
          <button onClick={onClose} className="text-[#4a6070] hover:text-[#e8f0f5]">✕</button>
        </div>
        <p className="text-[11px] text-[#4a6070] uppercase tracking-wider mb-3">
          Reasoning (from AI Scorer Agent)
        </p>
        <ul className="space-y-2">
          {(data?.reasons || []).map((r, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-[#e8f0f5]">
              <span className="text-[#00d4aa] mt-0.5 shrink-0">•</span>
              <span>{r}</span>
            </li>
          ))}
        </ul>
        <div className="mt-4 pt-4 border-t border-[#1a2530]">
          <p className="text-[11px] text-[#4a6070]">
            Weight: {((data?.weight || 0) * 100).toFixed(0)}% · 
            Contribution: {fmt((data?.score || 0) * (data?.weight || 0), 1)}/100
          </p>
        </div>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function Results() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [explainer, setExplainer] = useState(null)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    const fetch = async () => {
      try {
        const { data: res } = await axios.get(`${API}/appraisal/${jobId}/results`)
        setData(res)
      } catch (err) {
        if (err.response?.status === 202) {
          setTimeout(fetch, 3000)
          return
        }
        setError(err.response?.data?.detail || 'Failed to load results.')
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [jobId])

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const res = await axios.get(`${API}/appraisal/${jobId}/download`, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = res.headers['content-disposition']?.split('filename=')[1] || `CAM_${jobId}.docx`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      alert('Download failed. Please try again.')
    } finally {
      setDownloading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-[#00d4aa]/30 border-t-[#00d4aa] rounded-full animate-spin mx-auto mb-4" />
          <p className="text-[#4a6070] font-mono text-sm">Loading results...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto px-8 py-16 text-center">
        <p className="text-[#ef476f] mb-4">{error}</p>
        <button onClick={() => navigate('/appraisal/new')} className="btn-secondary">
          ← New Appraisal
        </button>
      </div>
    )
  }

  if (!data) return null

  const rec = data.final_recommendation || {}
  const scores = data.five_cs_scores || {}
  const extracted = data.extracted_financials || {}
  const fin = extracted.financials || {}
  const research = data.research_findings || {}
  const flags = extracted.red_flags || []
  const arb = data.arbitration_result || {}
  const overrideApplied = data.override_applied
  const preOverride = data.pre_override_scores || {}
  const turnaround = calcTurnaround(data.started_at, data.completed_at)

  const revenue = fin.revenue_3yr || [0, 0, 0]
  const ebitda = fin.ebitda_3yr || [0, 0, 0]
  const pat = fin.pat_3yr || [0, 0, 0]
  const years = ['FY22', 'FY23', 'FY24']
  const barData = years.map((yr, i) => ({
    yr,
    Revenue: Number(revenue[i] || 0).toFixed(2),
    EBITDA: Number(ebitda[i] || 0).toFixed(2),
    PAT: Number(pat[i] || 0).toFixed(2),
  }))

  const supplementary = scores.supplementary || {}
  const shap = scores.shap_attributions || {}

  const C_ORDER = ['character', 'capacity', 'capital', 'collateral', 'conditions']
  const C_WEIGHTS = { character: 25, capacity: 30, capital: 20, collateral: 15, conditions: 10 }

  return (
    <div className="max-w-6xl mx-auto px-8 py-8 animate-fade-in">
      {/* Explainer Modal */}
      {explainer && (
        <ExplainerPopup
          c={explainer}
          data={scores[explainer]}
          show={true}
          onClose={() => setExplainer(null)}
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-syne font-bold text-2xl text-[#e8f0f5]">
            {data.company_name || 'Appraisal Results'}
          </h1>
          <p className="text-[#4a6070] text-sm mt-1">
            {data.sector} · Job {jobId}
            {turnaround && (
              <span className="ml-3 text-[#00d4aa] font-mono">
                ⚡ Completed in {turnaround} vs industry avg 10–15 days
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => navigate('/appraisal/new')} className="btn-secondary text-sm py-2 px-4">
            ← New
          </button>
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="btn-primary text-sm py-2 px-5 flex items-center gap-2"
          >
            {downloading ? (
              <>
                <span className="w-3.5 h-3.5 border border-[#020608]/40 border-t-[#020608] rounded-full animate-spin" />
                Downloading...
              </>
            ) : (
              <>📥 Download CAM</>
            )}
          </button>
        </div>
      </div>

      {/* Decision Banner */}
      <DecisionBanner
        recommendation={rec.recommendation}
        loanAmount={rec.suggested_loan_amount}
        interestRate={rec.suggested_interest_rate}
      />

      {/* Arbitration Conflict Notice */}
      {arb.conflict_detected && (
        <div className="mb-6 rounded-xl border border-[#ef476f]/30 bg-[#ef476f]/8 px-6 py-4 animate-slide-up">
          <p className="font-syne font-bold text-[#ef476f] text-sm mb-1">⚡ Conflict Detected & Resolved</p>
          <p className="text-xs text-[#4a6070]">{arb.reconciliation_reasoning}</p>
          <p className="text-[11px] text-[#4a6070] mt-1 font-mono">
            Decision favored: {arb.favors} · Risk weight adjusted: {arb.adjusted_risk_weight}x
          </p>
        </div>
      )}

      {/* Qualitative Override */}
      {overrideApplied && preOverride.adjustments?.length > 0 && (
        <div className="mb-6 rounded-xl border border-[#ffd166]/30 bg-[#ffd166]/8 px-6 py-4 animate-slide-up">
          <p className="font-syne font-bold text-[#ffd166] text-sm mb-2">📋 Qualitative Override Applied</p>
          <p className="text-[11px] text-[#4a6070] mb-2">
            Credit officer notes influenced the following score adjustments:
          </p>
          {preOverride.adjustments.map((adj, i) => (
            <p key={i} className="text-xs text-[#e8f0f5] flex items-start gap-2">
              <span className="text-[#ffd166] shrink-0">→</span> {adj}
            </p>
          ))}
        </div>
      )}

      {/* Main content grid */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Five Cs Radar */}
        <div className="card p-6">
          <h2 className="font-syne font-semibold text-[#e8f0f5] mb-1">Five Cs Radar</h2>
          <p className="text-[11px] text-[#4a6070] mb-4">Click any C below to see full reasoning</p>
          <FiveCsRadar scores={scores} />
          <div className="flex flex-wrap gap-2 mt-4 justify-center">
            {C_ORDER.map((c) => (
              <button
                key={c}
                onClick={() => setExplainer(c)}
                className="text-[11px] px-3 py-1.5 rounded-full border border-[#1a2530] text-[#4a6070] hover:border-[#00d4aa] hover:text-[#00d4aa] transition-colors cursor-pointer"
              >
                {c.charAt(0).toUpperCase() + c.slice(1)}: <span className="font-mono">{scores[c]?.score || 0}</span>
              </button>
            ))}
          </div>
        </div>

        {/* 3-Year Revenue Bar Chart */}
        <div className="card p-6">
          <h2 className="font-syne font-semibold text-[#e8f0f5] mb-4">3-Year Financial Performance</h2>
          <div style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData} margin={{ top: 0, right: 0, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a2530" />
                <XAxis dataKey="yr" tick={{ fill: '#4a6070', fontSize: 11 }} />
                <YAxis tick={{ fill: '#4a6070', fontSize: 10 }} />
                <ReTooltip
                  contentStyle={{ background: '#0a0f12', border: '1px solid #1a2530', borderRadius: 8, fontSize: 11 }}
                  labelStyle={{ color: '#e8f0f5' }}
                />
                <Bar dataKey="Revenue" fill="#0099ff" radius={[4,4,0,0]} />
                <Bar dataKey="EBITDA" fill="#00d4aa" radius={[4,4,0,0]} />
                <Bar dataKey="PAT" fill="#a78bfa" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex gap-4 mt-3 justify-center">
            {[['Revenue', '#0099ff'], ['EBITDA', '#00d4aa'], ['PAT', '#a78bfa']].map(([l, c]) => (
              <div key={l} className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-sm" style={{ background: c }} />
                <span className="text-[11px] text-[#4a6070]">{l}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Key Metrics Row */}
      <div className="grid grid-cols-5 gap-3 mb-6">
        <MetricCard
          label="DSCR"
          value={fmt(supplementary.dscr || fin.dscr, 2)}
          unit="x"
          sub={Number(supplementary.dscr || fin.dscr) >= 1.25 ? 'Adequate ✓' : 'Below threshold ✗'}
          color={Number(supplementary.dscr || fin.dscr) >= 1.25 ? '#00d4aa' : '#ef476f'}
        />
        <MetricCard
          label="Debt / Equity"
          value={fmt(supplementary.debt_to_equity || fin.debt_to_equity, 2)}
          unit="x"
          sub={Number(supplementary.debt_to_equity || fin.debt_to_equity) <= 3 ? 'Acceptable ✓' : 'High ✗'}
          color={Number(supplementary.debt_to_equity || fin.debt_to_equity) <= 3 ? '#00d4aa' : '#ef476f'}
        />
        <MetricCard
          label="Revenue CAGR"
          value={supplementary.revenue_cagr_pct ? fmt(supplementary.revenue_cagr_pct, 1) : '—'}
          unit="%"
          color="#0099ff"
        />
        <MetricCard
          label="Collateral Cover"
          value={supplementary.collateral_cover ? fmt(supplementary.collateral_cover, 2) : '—'}
          unit="x"
          color={Number(supplementary.collateral_cover) >= 1.5 ? '#00d4aa' : '#ffd166'}
        />
        <MetricCard
          label="Promoter Score"
          value={supplementary.promoter_integrity_score ?? research.promoter_integrity_score ?? '—'}
          unit="/100"
          color={Number(supplementary.promoter_integrity_score) >= 60 ? '#00d4aa' : '#ef476f'}
        />
      </div>

      {/* Red Flags */}
      {flags.length > 0 && (
        <div className="card p-6 mb-6">
          <h2 className="font-syne font-semibold text-[#e8f0f5] mb-4">
            ⚠ Risk Flags ({flags.length})
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {flags.map((flag, i) => (
              <RedFlagCard key={i} flag={flag} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* Research Findings */}
      {research.key_findings?.length > 0 && (
        <div className="card p-6 mb-6">
          <h2 className="font-syne font-semibold text-[#e8f0f5] mb-4">
            🔍 Research Findings
          </h2>
          <div className="space-y-3">
            {research.key_findings.map((f, i) => (
              <RedFlagCard
                key={i}
                flag={f.finding}
                severity={f.severity}
                source={f.source}
                index={i}
              />
            ))}
          </div>
          {research.recommendation_impact && (
            <p className="text-xs text-[#4a6070] mt-4 pl-1">
              Impact: {research.recommendation_impact}
            </p>
          )}
        </div>
      )}

      {/* Why This Decision */}
      <div className="card p-6 mb-6">
        <h2 className="font-syne font-semibold text-[#e8f0f5] mb-4">💡 Why This Decision?</h2>
        <p className="text-sm text-[#e8f0f5] leading-relaxed">{rec.decision_reason || 'No reasoning provided.'}</p>
        {rec.overriding_factors?.length > 0 && (
          <div className="mt-4 pt-4 border-t border-[#1a2530]">
            <p className="text-[11px] text-[#4a6070] uppercase tracking-wider mb-2">Overriding Factors</p>
            {rec.overriding_factors.map((f, i) => (
              <p key={i} className="text-xs text-[#ef476f] flex items-start gap-2 mb-1">
                <span className="shrink-0 mt-0.5">⚡</span> {f}
              </p>
            ))}
          </div>
        )}
      </div>

      {/* Score Breakdown Table */}
      <div className="card p-6 mb-6">
        <h2 className="font-syne font-semibold text-[#e8f0f5] mb-4">📊 Score Breakdown</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1a2530]">
                {['Five C', 'Score /100', 'Weight', 'Weighted Score', 'SHAP Attribution', ''].map((h) => (
                  <th key={h} className="text-left px-4 py-2.5 text-[10px] uppercase tracking-widest text-[#4a6070] font-mono">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {C_ORDER.map((c) => {
                const cd = scores[c] || {}
                const s = Number(cd.score || 0)
                const w = cd.weight || C_WEIGHTS[c] / 100
                const ws = s * w
                const attr = shap[c] || 0
                return (
                  <tr
                    key={c}
                    className="border-b border-[#1a2530]/40 hover:bg-[#111820] cursor-pointer transition-colors"
                    onClick={() => setExplainer(c)}
                  >
                    <td className="px-4 py-3 font-semibold text-[#e8f0f5] capitalize">{c}</td>
                    <td className="px-4 py-3 font-mono text-[#00d4aa]">{s.toFixed(0)}</td>
                    <td className="px-4 py-3 font-mono text-[#4a6070]">{C_WEIGHTS[c]}%</td>
                    <td className="px-4 py-3 font-mono text-[#e8f0f5]">{ws.toFixed(1)}</td>
                    <td className="px-4 py-3 font-mono">
                      <span className={attr >= 0 ? 'text-[#00d4aa]' : 'text-[#ef476f]'}>
                        {attr >= 0 ? '+' : ''}{attr.toFixed(2)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[#4a6070] text-xs hover:text-[#00d4aa]">→ explain</td>
                  </tr>
                )
              })}
              <tr className="border-t-2 border-[#1a2530]">
                <td className="px-4 py-3 font-syne font-bold text-[#e8f0f5]">TOTAL</td>
                <td className="px-4 py-3" />
                <td className="px-4 py-3 font-mono text-[#4a6070]">100%</td>
                <td className="px-4 py-3 font-mono font-bold text-[#00d4aa] text-base">
                  {fmt(scores.weighted_total, 1)}
                </td>
                <td className="px-4 py-3" />
                <td />
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Download CTA */}
      <div className="card p-6 flex items-center justify-between">
        <div>
          <h3 className="font-syne font-semibold text-[#e8f0f5]">Credit Appraisal Memo</h3>
          <p className="text-xs text-[#4a6070] mt-1">
            Full Word document with all sections, tables, and recommendations.
          </p>
        </div>
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="btn-primary px-8 py-3 flex items-center gap-2"
        >
          {downloading ? (
            <>
              <span className="w-4 h-4 border-2 border-[#020608]/40 border-t-[#020608] rounded-full animate-spin" />
              Generating...
            </>
          ) : (
            '📥 Download CAM (.docx)'
          )}
        </button>
      </div>
    </div>
  )
}
