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

// Helper function to safely extract error messages from API responses
const getErrorMessage = (err, fallback = 'An error occurred') => {
  if (typeof err === 'string') return err
  
  const detail = err.response?.data?.detail
  if (!detail) return fallback
  
  // If detail is a string, return it
  if (typeof detail === 'string') return detail
  
  // If detail is an array of validation errors (FastAPI format)
  if (Array.isArray(detail)) {
    return detail.map(e => e.msg || JSON.stringify(e)).join(', ')
  }
  
  // If detail is an object, try to extract message
  if (typeof detail === 'object') {
    return detail.msg || detail.message || JSON.stringify(detail)
  }
  
  return fallback
}

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

function ConfidenceIndicator({ confidence }) {
  // Show 5 circles, filled based on confidence (every 20%)
  const filled = Math.ceil((confidence || 0) * 5)
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((i) => (
        <span
          key={i}
          className={`w-2 h-2 rounded-full ${
            i <= filled ? 'bg-[#00d4aa]' : 'bg-[#1a2530]'
          }`}
        />
      ))}
      <span className="ml-1.5 text-xs font-mono text-[#4a6070]">
        {((confidence || 0) * 100).toFixed(0)}%
      </span>
    </div>
  )
}

function MethodBadge({ method }) {
  const config = {
    table_exact_match: { label: 'Table', bg: 'bg-[#00d4aa]/10', text: 'text-[#00d4aa]', border: 'border-[#00d4aa]/30' },
    table_fuzzy_match: { label: 'Table', bg: 'bg-[#00d4aa]/10', text: 'text-[#00d4aa]', border: 'border-[#00d4aa]/30' },
    text_regex: { label: 'Regex', bg: 'bg-[#ffd166]/10', text: 'text-[#ffd166]', border: 'border-[#ffd166]/30' },
    ai_extraction: { label: 'Gemini AI', bg: 'bg-[#a855f7]/10', text: 'text-[#a855f7]', border: 'border-[#a855f7]/30' },
    ocr: { label: 'OCR', bg: 'bg-[#0099ff]/10', text: 'text-[#0099ff]', border: 'border-[#0099ff]/30' },
    not_found: { label: '—', bg: 'bg-[#1a2530]', text: 'text-[#4a6070]', border: 'border-[#1a2530]' },
  }
  const c = config[method] || config.not_found
  return (
    <span className={`px-2 py-1 rounded text-[10px] font-mono border ${c.bg} ${c.text} ${c.border}`}>
      {c.label}
    </span>
  )
}

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
        setError(getErrorMessage(err, 'Failed to load results.'))
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
      a.download = res.headers['content-disposition']?.split('filename=')[1] || `CAM_${jobId}.pdf`
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

  // ── Step 1: Read financial data with flat structure (new) and nested fallback (old) ──
  const extracted = data.extracted_financials || {}
  const fin = extracted.financials || {}
  
  // Try flat structure first, fallback to nested
  const revenue = extracted.revenue_3yr || fin.revenue_3yr || [0, 0, 0]
  const ebitda = extracted.ebitda_3yr || fin.ebitda_3yr || [0, 0, 0]
  const pat = extracted.pat_3yr || fin.pat_3yr || [0, 0, 0]
  const dscr = extracted.dscr || fin.dscr || 0
  const debtToEquity = extracted.debt_to_equity || fin.debt_to_equity || 0
  const revenueCagr = extracted.revenue_cagr || fin.revenue_cagr || 0
  const collateralCoverage = extracted.collateral_coverage || fin.collateral_coverage || 0
  
  // ── Step 2: Read Five Cs scores with multiple fallback locations ──
  const scorecard = data.scorecard_result || {}
  const fiveC = data.five_cs_scores || scorecard.five_cs_scores || scorecard.five_c_scores || {}
  
  // ── Step 3: Read decision rationale ──
  const decisionRationale = data.decision_rationale || scorecard.decision_rationale || "No reasoning provided"
  
  // ── Step 4: Other data ──
  const rec = data.final_recommendation || {}
  const research = data.research_findings || {}
  const flags = extracted.red_flags || []
  const arb = data.arbitration_result || {}
  const overrideApplied = data.override_applied
  const preOverride = data.pre_override_scores || {}
  const turnaround = calcTurnaround(data.started_at, data.completed_at)
  
  // Build 3-year financial chart data
  const years = ['FY22', 'FY23', 'FY24']
  const barData = years.map((yr, i) => ({
    yr,
    Revenue: Number(revenue[i] || 0).toFixed(2),
    EBITDA: Number(ebitda[i] || 0).toFixed(2),
    PAT: Number(pat[i] || 0).toFixed(2),
  }))

  const supplementary = fiveC.supplementary || {}
  const shap = data.shap_attribution || {}

  const getCScore = (c) => {
    const raw = fiveC[c]
    return Number(typeof raw === 'object' ? raw?.score : raw) || 0
  }

  const C_ORDER = ['character', 'capacity', 'capital', 'collateral', 'conditions']
  const C_WEIGHTS = { character: 25, capacity: 30, capital: 20, collateral: 15, conditions: 10 }

  return (
    <div className="max-w-6xl mx-auto px-8 py-8 animate-fade-in">
      {/* Explainer Modal */}
      {explainer && (
        <ExplainerPopup
          c={explainer}
          data={fiveC[explainer]}
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
          <FiveCsRadar scores={fiveC} />
          <div className="flex flex-wrap gap-2 mt-4 justify-center">
            {C_ORDER.map((c) => (
              <button
                key={c}
                onClick={() => setExplainer(c)}
                className="text-[11px] px-3 py-1.5 rounded-full border border-[#1a2530] text-[#4a6070] hover:border-[#00d4aa] hover:text-[#00d4aa] transition-colors cursor-pointer"
              >
                {c.charAt(0).toUpperCase() + c.slice(1)}: <span className="font-mono">{getCScore(c)}</span>
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
          value={fmt(dscr, 2)}
          unit="x"
          sub={Number(dscr) >= 1.25 ? 'Adequate ✓' : 'Below threshold ✗'}
          color={Number(dscr) >= 1.25 ? '#00d4aa' : '#ef476f'}
        />
        <MetricCard
          label="Debt / Equity"
          value={fmt(debtToEquity, 2)}
          unit="x"
          sub={Number(debtToEquity) <= 3 ? 'Acceptable ✓' : 'High ✗'}
          color={Number(debtToEquity) <= 3 ? '#00d4aa' : '#ef476f'}
        />
        <MetricCard
          label="Revenue CAGR"
          value={revenueCagr ? fmt(revenueCagr, 1) : '—'}
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

      {/* SWOT Analysis Grid */}
      {data.swot_analysis && (
        <div className="card p-6 mb-6">
          <h2 className="font-syne font-semibold text-[#e8f0f5] mb-4">
            🎯 SWOT Analysis
          </h2>
          
          {/* Overall Assessment */}
          {data.swot_analysis.overall_assessment && (
            <div className="mb-6 p-4 rounded-lg border border-[#1a2530] bg-[#0d1419]">
              <p className="text-sm text-[#e8f0f5] leading-relaxed">
                {data.swot_analysis.overall_assessment}
              </p>
            </div>
          )}

          {/* 2x2 Grid */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            {/* Strengths - Green */}
            <div className="p-5 rounded-lg border-2 border-[#00d4aa]/30 bg-[#00d4aa]/5">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center" 
                     style={{ background: 'linear-gradient(135deg, #00d4aa, #00aa88)' }}>
                  <span className="text-white font-bold text-lg">✓</span>
                </div>
                <h3 className="font-syne font-semibold text-[#00d4aa] text-lg">STRENGTHS</h3>
              </div>
              <ul className="space-y-2">
                {(data.swot_analysis.strengths || []).slice(0, 3).map((strength, i) => (
                  <li key={i} className="text-xs text-[#e8f0f5] flex items-start gap-2">
                    <span className="text-[#00d4aa] shrink-0 mt-0.5">•</span>
                    <span>{strength}</span>
                  </li>
                ))}
              </ul>
              {data.swot_analysis.strengths?.length > 3 && (
                <p className="text-xs text-[#4a6070] mt-2">
                  +{data.swot_analysis.strengths.length - 3} more in CAM report
                </p>
              )}
            </div>

            {/* Weaknesses - Red */}
            <div className="p-5 rounded-lg border-2 border-[#ef476f]/30 bg-[#ef476f]/5">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center" 
                     style={{ background: 'linear-gradient(135deg, #ef476f, #c73659)' }}>
                  <span className="text-white font-bold text-lg">⚠</span>
                </div>
                <h3 className="font-syne font-semibold text-[#ef476f] text-lg">WEAKNESSES</h3>
              </div>
              <ul className="space-y-2">
                {(data.swot_analysis.weaknesses || []).slice(0, 3).map((weakness, i) => (
                  <li key={i} className="text-xs text-[#e8f0f5] flex items-start gap-2">
                    <span className="text-[#ef476f] shrink-0 mt-0.5">•</span>
                    <span>{weakness}</span>
                  </li>
                ))}
              </ul>
              {data.swot_analysis.weaknesses?.length > 3 && (
                <p className="text-xs text-[#4a6070] mt-2">
                  +{data.swot_analysis.weaknesses.length - 3} more in CAM report
                </p>
              )}
            </div>

            {/* Opportunities - Blue */}
            <div className="p-5 rounded-lg border-2 border-[#0099ff]/30 bg-[#0099ff]/5">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center" 
                     style={{ background: 'linear-gradient(135deg, #0099ff, #0077cc)' }}>
                  <span className="text-white font-bold text-lg">↗</span>
                </div>
                <h3 className="font-syne font-semibold text-[#0099ff] text-lg">OPPORTUNITIES</h3>
              </div>
              <ul className="space-y-2">
                {(data.swot_analysis.opportunities || []).slice(0, 3).map((opportunity, i) => (
                  <li key={i} className="text-xs text-[#e8f0f5] flex items-start gap-2">
                    <span className="text-[#0099ff] shrink-0 mt-0.5">•</span>
                    <span>{opportunity}</span>
                  </li>
                ))}
              </ul>
              {data.swot_analysis.opportunities?.length > 3 && (
                <p className="text-xs text-[#4a6070] mt-2">
                  +{data.swot_analysis.opportunities.length - 3} more in CAM report
                </p>
              )}
            </div>

            {/* Threats - Orange */}
            <div className="p-5 rounded-lg border-2 border-[#ff9500]/30 bg-[#ff9500]/5">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center" 
                     style={{ background: 'linear-gradient(135deg, #ff9500, #dd7700)' }}>
                  <span className="text-white font-bold text-lg">↘</span>
                </div>
                <h3 className="font-syne font-semibold text-[#ff9500] text-lg">THREATS</h3>
              </div>
              <ul className="space-y-2">
                {(data.swot_analysis.threats || []).slice(0, 3).map((threat, i) => (
                  <li key={i} className="text-xs text-[#e8f0f5] flex items-start gap-2">
                    <span className="text-[#ff9500] shrink-0 mt-0.5">•</span>
                    <span>{threat}</span>
                  </li>
                ))}
              </ul>
              {data.swot_analysis.threats?.length > 3 && (
                <p className="text-xs text-[#4a6070] mt-2">
                  +{data.swot_analysis.threats.length - 3} more in CAM report
                </p>
              )}
            </div>
          </div>

          {/* Key Consideration */}
          {data.swot_analysis.key_consideration && (
            <div className="p-4 rounded-lg border-2 border-[#ff6900]/40 bg-[#ff6900]/10">
              <div className="flex items-start gap-3">
                <span className="text-2xl shrink-0">🔑</span>
                <div>
                  <p className="text-xs text-[#4a6070] uppercase tracking-wider mb-1 font-mono">
                    KEY CONSIDERATION
                  </p>
                  <p className="text-sm text-[#e8f0f5] font-semibold">
                    {data.swot_analysis.key_consideration}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Extraction Quality - Document Intelligence Pipeline */}
      {data.ingestion_summary && (
        <div className="card p-6 mb-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center" 
                 style={{ background: 'linear-gradient(135deg, #00d4aa, #0099ff)' }}>
              <span className="text-white text-xl">🔬</span>
            </div>
            <div>
              <h2 className="font-syne font-semibold text-[#e8f0f5]">
                Extraction Quality
              </h2>
              <p className="text-xs text-[#4a6070] mt-0.5">
                8-Stage Document Intelligence Pipeline · CLAHE + Hough + PaddleOCR
              </p>
            </div>
          </div>

          {/* Ingestion Summary Card */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="p-4 rounded-lg border border-[#1a2530] bg-[#0d1419]">
              <p className="text-[10px] text-[#4a6070] uppercase tracking-wider mb-1 font-mono">
                Documents Processed
              </p>
              <p className="font-mono text-2xl text-[#e8f0f5]">
                {data.ingestion_summary.total_documents}
              </p>
            </div>
            <div className="p-4 rounded-lg border border-[#1a2530] bg-[#0d1419]">
              <p className="text-[10px] text-[#4a6070] uppercase tracking-wider mb-1 font-mono">
                Avg Completeness
              </p>
              <p className="font-mono text-2xl text-[#00d4aa]">
                {data.ingestion_summary.avg_completion_pct?.toFixed(1) || 0}%
              </p>
            </div>
            <div className="p-4 rounded-lg border border-[#1a2530] bg-[#0d1419]">
              <p className="text-[10px] text-[#4a6070] uppercase tracking-wider mb-1 font-mono">
                Schema-Guided Extraction
              </p>
              <p className="font-mono text-2xl text-[#e8f0f5]">
                {data.ingestion_summary.schema_guided_count || 0} docs
              </p>
            </div>
          </div>

          {/* Confidence Distribution */}
          {data.ingestion_summary.schema_guided_count > 0 && (
            <div className="mb-6 p-4 rounded-lg border border-[#1a2530] bg-[#0d1419]">
              <p className="text-xs text-[#4a6070] uppercase tracking-wider mb-3 font-mono">
                Confidence Distribution
              </p>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#00d4aa]" />
                  <span className="text-sm text-[#e8f0f5]">
                    High (≥80%): <span className="font-mono font-bold">{data.ingestion_summary.high_confidence_count || 0}</span>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#ffd166]" />
                  <span className="text-sm text-[#e8f0f5]">
                    Medium (50-80%): <span className="font-mono font-bold">{data.ingestion_summary.medium_confidence_count || 0}</span>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#ef476f]" />
                  <span className="text-sm text-[#e8f0f5]">
                    Low (&lt;50%): <span className="font-mono font-bold">{data.ingestion_summary.low_confidence_count || 0}</span>
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Schema Extraction Results */}
          {data.schema_extraction_results && Object.keys(data.schema_extraction_results).length > 0 && (
            <div className="mb-6">
              <p className="text-sm text-[#e8f0f5] font-semibold mb-3">
                📋 Schema-Guided Extraction Results
              </p>
              <div className="space-y-3">
                {Object.entries(data.schema_extraction_results).map(([fileId, result]) => {
                  const completion = result.completion_percentage || 0
                  const barColor = completion >= 80 ? '#00d4aa' : completion >= 50 ? '#ffd166' : '#ef476f'
                  const totalFields = Object.keys(result.fields || {}).length
                  const extractedFields = Object.values(result.fields || {}).filter(f => f.status === 'EXTRACTED').length
                  
                  return (
                    <details key={fileId} className="group">
                      <summary className="cursor-pointer p-4 rounded-lg border border-[#1a2530] bg-[#0d1419] hover:bg-[#111820] transition-colors">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="text-sm text-[#e8f0f5] font-mono">
                                {result.schema_name || 'Unknown Schema'}
                              </span>
                              <span className="text-[10px] text-[#4a6070] font-mono">
                                {fileId.slice(0, 8)}...
                              </span>
                            </div>
                            <div className="flex items-center gap-3">
                              <div className="flex-1 h-2 rounded-full bg-[#1a2530] overflow-hidden">
                                <div 
                                  className="h-full transition-all"
                                  style={{ 
                                    width: `${completion}%`,
                                    background: `linear-gradient(90deg, ${barColor}, ${barColor}aa)`
                                  }}
                                />
                              </div>
                              <span className="text-xs font-mono text-[#e8f0f5] whitespace-nowrap">
                                {completion.toFixed(1)}%
                              </span>
                            </div>
                          </div>
                          <span className="ml-4 text-[10px] text-[#4a6070] font-mono">
                            {extractedFields}/{totalFields} fields
                          </span>
                        </div>
                      </summary>
                      
                      {/* Field-level details */}
                      <div className="mt-2 p-4 rounded-lg border border-[#1a2530] bg-[#0a0e12]">
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="border-b border-[#1a2530]">
                                <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-[#4a6070] font-mono">
                                  Field
                                </th>
                                <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-[#4a6070] font-mono">
                                  Extracted Value
                                </th>
                                <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-[#4a6070] font-mono">
                                  Method
                                </th>
                                <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-[#4a6070] font-mono">
                                  Confidence
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(result.fields || {}).map(([fieldName, fieldData]) => {
                                const isMissing = fieldData.status === 'MISSING'
                                const isLowConf = !isMissing && (fieldData.confidence || 0) < 0.5
                                const rowBg = isMissing ? 'bg-[#ef476f]/5' : isLowConf ? 'bg-[#ffd166]/5' : ''
                                
                                return (
                                  <tr key={fieldName} className={`border-b border-[#1a2530]/40 ${rowBg}`}>
                                    <td className="px-3 py-2.5 text-[#e8f0f5]">
                                      {fieldData.field_label || fieldName}
                                    </td>
                                    <td className="px-3 py-2.5 font-mono">
                                      {isMissing ? (
                                        <span className="text-[#ef476f] italic">NOT FOUND</span>
                                      ) : (
                                        <span className="text-[#e8f0f5]">
                                          {String(fieldData.value || '—').substring(0, 50)}
                                        </span>
                                      )}
                                    </td>
                                    <td className="px-3 py-2.5">
                                      <MethodBadge method={fieldData.extraction_method} />
                                    </td>
                                    <td className="px-3 py-2.5">
                                      {isMissing ? (
                                        <span className="text-[10px] text-[#4a6070] font-mono">—</span>
                                      ) : (
                                        <ConfidenceIndicator confidence={fieldData.confidence} />
                                      )}
                                    </td>
                                  </tr>
                                )
                              })}
                            </tbody>
                          </table>
                        </div>
                        
                        {result.missing_required_fields?.length > 0 && (
                          <div className="mt-3 p-3 rounded border border-[#ef476f]/30 bg-[#ef476f]/5">
                            <p className="text-[10px] uppercase tracking-wider text-[#ef476f] mb-1 font-mono">
                              Missing Required Fields
                            </p>
                            <p className="text-xs text-[#e8f0f5]">
                              {result.missing_required_fields.join(', ')}
                            </p>
                          </div>
                        )}
                      </div>
                    </details>
                  )
                })}
              </div>
            </div>
          )}

          {/* 3-Way Revenue Reconciliation */}
          {extracted.gst_vs_bank_discrepancy && (
            <div className="mb-6">
              <p className="text-sm text-[#e8f0f5] font-semibold mb-3">
                ⚖️ 3-Way Revenue Reconciliation
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-[#1a2530]">
                      <th className="text-left px-4 py-3 text-[10px] uppercase tracking-wider text-[#4a6070] font-mono">
                        Source
                      </th>
                      <th className="text-left px-4 py-3 text-[10px] uppercase tracking-wider text-[#4a6070] font-mono">
                        Revenue Value
                      </th>
                      <th className="text-left px-4 py-3 text-[10px] uppercase tracking-wider text-[#4a6070] font-mono">
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* GSTR-3B (Self-declared) */}
                    <tr className="border-b border-[#1a2530]/40">
                      <td className="px-4 py-3 text-[#e8f0f5]">
                        GSTR-3B (Self-declared)
                      </td>
                      <td className="px-4 py-3 font-mono text-[#e8f0f5]">
                        ₹{(extracted.gst_vs_bank_discrepancy.gstr3b_total || 0).toFixed(2)} Cr
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-[#00d4aa]">✓ Base</span>
                      </td>
                    </tr>
                    
                    {/* GSTR-2A (Auto-populated) */}
                    {extracted.gst_vs_bank_discrepancy.gstr2a_total > 0 && (
                      <tr className="border-b border-[#1a2530]/40">
                        <td className="px-4 py-3 text-[#e8f0f5]">
                          GSTR-2A (Auto-populated)
                        </td>
                        <td className="px-4 py-3 font-mono text-[#e8f0f5]">
                          ₹{(extracted.gst_vs_bank_discrepancy.gstr2a_total || 0).toFixed(2)} Cr
                        </td>
                        <td className="px-4 py-3">
                          {extracted.gst_vs_bank_discrepancy.discrepancy_pct <= 5 ? (
                            <span className="text-[#00d4aa]">
                              ✓ {Math.abs(extracted.gst_vs_bank_discrepancy.discrepancy_pct).toFixed(1)}% variance — within 5% threshold
                            </span>
                          ) : extracted.gst_vs_bank_discrepancy.discrepancy_pct <= 15 ? (
                            <span className="text-[#ffd166]">
                              ⚠ {Math.abs(extracted.gst_vs_bank_discrepancy.discrepancy_pct).toFixed(1)}% variance — within 15% threshold
                            </span>
                          ) : (
                            <span className="text-[#ef476f]">
                              ✕ {Math.abs(extracted.gst_vs_bank_discrepancy.discrepancy_pct).toFixed(1)}% variance — exceeds 15% threshold
                            </span>
                          )}
                        </td>
                      </tr>
                    )}
                    
                    {/* Financial Statement */}
                    {fin.revenue && (
                      <tr className="border-b border-[#1a2530]/40">
                        <td className="px-4 py-3 text-[#e8f0f5]">
                          Financial Statement (Latest FY)
                        </td>
                        <td className="px-4 py-3 font-mono text-[#e8f0f5]">
                          ₹{(fin.revenue || 0).toFixed(2)} Cr
                        </td>
                        <td className="px-4 py-3">
                          {(() => {
                            const gstBase = extracted.gst_vs_bank_discrepancy.gstr3b_total || 0
                            const variance = gstBase > 0 ? ((fin.revenue - gstBase) / gstBase) * 100 : 0
                            if (Math.abs(variance) <= 10) {
                              return <span className="text-[#00d4aa]">✓ {Math.abs(variance).toFixed(1)}% variance — within 10% threshold</span>
                            } else if (Math.abs(variance) <= 20) {
                              return <span className="text-[#ffd166]">⚠ {Math.abs(variance).toFixed(1)}% variance — within 20% threshold</span>
                            } else {
                              return <span className="text-[#ef476f]">✕ {Math.abs(variance).toFixed(1)}% variance — exceeds 20% threshold</span>
                            }
                          })()}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              
              {extracted.gst_vs_bank_discrepancy.detected && (
                <div className={`mt-3 p-3 rounded border ${
                  extracted.gst_vs_bank_discrepancy.severity === 'HIGH' 
                    ? 'border-[#ef476f]/30 bg-[#ef476f]/5' 
                    : 'border-[#ffd166]/30 bg-[#ffd166]/5'
                }`}>
                  <p className={`text-xs font-semibold mb-1 ${
                    extracted.gst_vs_bank_discrepancy.severity === 'HIGH' ? 'text-[#ef476f]' : 'text-[#ffd166]'
                  }`}>
                    ⚠ {extracted.gst_vs_bank_discrepancy.severity} Severity Discrepancy
                  </p>
                  <p className="text-xs text-[#4a6070]">
                    {extracted.gst_vs_bank_discrepancy.details}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Document Quality Insights */}
          {extracted.document_quality_summary && (
            <div className="p-4 rounded-lg border border-[#0099ff]/30 bg-[#0099ff]/5">
              <div className="flex items-start gap-3">
                <span className="text-xl shrink-0">💡</span>
                <div className="flex-1">
                  <p className="text-xs text-[#0099ff] uppercase tracking-wider mb-1 font-mono">
                    Pipeline Innovation
                  </p>
                  <p className="text-sm text-[#e8f0f5]">
                    Your system uses <strong>CLAHE contrast enhancement</strong> → <strong>Hough Line Transform deskewing</strong> → 
                    <strong> PaddleOCR with Tesseract fallback</strong> → <strong>4-tier confidence scoring</strong> (Table Exact 0.9 → 
                    Fuzzy 0.7 → Regex 0.6 → Gemini AI 0.5). This 8-stage pipeline provides <strong>transparent, auditable extraction</strong> — 
                    a competitive advantage other teams don't have.
                  </p>
                  {extracted.document_quality_summary.low_confidence_count > 0 && (
                    <p className="text-xs text-[#ffd166] mt-2">
                      ⚠ {extracted.document_quality_summary.low_confidence_count} document(s) flagged for manual review due to low quality.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Why This Decision */}
      <div className="card p-6 mb-6">
        <h2 className="font-syne font-semibold text-[#e8f0f5] mb-4">💡 Why This Decision?</h2>
        <p className="text-sm text-[#e8f0f5] leading-relaxed">{decisionRationale}</p>
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
                const score = getCScore(c)
                const weight = C_WEIGHTS[c] / 100
                const weightedScore = score * weight
                const attr = Number(shap[c]?.replace(/[+]/g, '') || 0)
                return (
                  <tr
                    key={c}
                    className="border-b border-[#1a2530]/40 hover:bg-[#111820] cursor-pointer transition-colors"
                    onClick={() => setExplainer(c)}
                  >
                    <td className="px-4 py-3 font-semibold text-[#e8f0f5] capitalize">{c}</td>
                    <td className="px-4 py-3 font-mono text-[#00d4aa]">{score.toFixed(0)}</td>
                    <td className="px-4 py-3 font-mono text-[#4a6070]">{C_WEIGHTS[c]}%</td>
                    <td className="px-4 py-3 font-mono text-[#e8f0f5]">{weightedScore.toFixed(1)}</td>
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
                  {fmt(C_ORDER.reduce((sum, c) => sum + (getCScore(c) * (C_WEIGHTS[c] / 100)), 0), 1)}
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
            Full PDF report with all sections, tables, and recommendations.
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
