/**
 * AgentBlock — displays a single agent's status in the Pipeline view.
 * Status: PENDING | RUNNING | DONE | ERROR
 */

const STATUS_CONFIG = {
  PENDING: {
    border: 'border-[#1a2530]',
    bg: 'bg-[#0a0f12]',
    dot: 'bg-[#4a6070]',
    label: 'Pending',
    labelColor: 'text-[#4a6070]',
  },
  RUNNING: {
    border: 'border-[#0099ff] agent-running-border',
    bg: 'bg-[#0a0f12]',
    dot: 'bg-[#0099ff] animate-pulse',
    label: 'Running',
    labelColor: 'text-[#0099ff]',
  },
  DONE: {
    border: 'border-[#00d4aa]',
    bg: 'bg-[#0a0f12]',
    dot: 'bg-[#00d4aa]',
    label: 'Done',
    labelColor: 'text-[#00d4aa]',
  },
  ERROR: {
    border: 'border-[#ef476f]',
    bg: 'bg-[#0a0f12]',
    dot: 'bg-[#ef476f]',
    label: 'Error',
    labelColor: 'text-[#ef476f]',
  },
}

const AGENT_META = {
  ingestor: {
    icon: '📄',
    title: 'Ingestor Agent',
    subtitle: 'Document Parsing & GST Check',
    tasks: [
      'Parse uploaded PDFs',
      'Extract financial tables',
      'GSTR-3B vs GSTR-2A reconciliation',
      'Rule-based flag detection',
    ],
  },
  research: {
    icon: '🔍',
    title: 'Research Agent',
    subtitle: 'Web Due Diligence (ReAct)',
    tasks: [
      'Fraud/NPA web search',
      'Promoter background check',
      'MCA / corporate filings',
      'Sector regulatory outlook',
    ],
  },
  scorer: {
    icon: '⚖️',
    title: 'Risk Scorer',
    subtitle: 'Five Cs of Credit Scoring',
    tasks: [
      'Character — promoter integrity',
      'Capacity — DSCR & revenue',
      'Capital — net worth & D/E',
      'Collateral & Conditions scoring',
    ],
  },
  cam_generator: {
    icon: '📝',
    title: 'CAM Generator',
    subtitle: 'Word Document Generation',
    tasks: [
      'Executive summary (Claude)',
      'Financial tables & ratios',
      'Five Cs narrative',
      'Export .docx report',
    ],
  },
}

export default function AgentBlock({ agentKey, status = 'PENDING', isLast = false }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.PENDING
  const meta = AGENT_META[agentKey] || {}

  return (
    <div className="flex items-start gap-0">
      <div
        className={`flex-1 rounded-xl border p-5 transition-all duration-500 animate-slide-up ${cfg.border} ${cfg.bg}`}
        style={{ minWidth: 180 }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-2xl">{meta.icon}</span>
          <div className="flex items-center gap-1.5">
            <span className={`status-dot ${cfg.dot}`} />
            <span className={`text-[10px] font-mono font-semibold uppercase tracking-wider ${cfg.labelColor}`}>
              {cfg.label}
            </span>
          </div>
        </div>

        {/* Title */}
        <div className="mb-1">
          <p className="font-syne font-bold text-sm text-[#e8f0f5]">{meta.title}</p>
          <p className="text-[11px] text-[#4a6070] mt-0.5">{meta.subtitle}</p>
        </div>

        {/* Task checklist */}
        <ul className="mt-3 space-y-1.5">
          {(meta.tasks || []).map((task, i) => (
            <li key={i} className="flex items-start gap-2 text-[11px]">
              <span className={`mt-0.5 text-[10px] ${status === 'DONE' ? 'text-[#00d4aa]' : 'text-[#4a6070]'}`}>
                {status === 'DONE' ? '✓' : '○'}
              </span>
              <span className={status === 'DONE' ? 'text-[#4a6070] line-through' : 'text-[#4a6070]'}>
                {task}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {/* Arrow connector */}
      {!isLast && (
        <div className="flex items-center self-center mt-0 px-1">
          <svg width="28" height="20" viewBox="0 0 28 20" fill="none">
            <path
              d="M0 10 H20 M14 4 L20 10 L14 16"
              stroke={status === 'DONE' ? '#00d4aa' : '#1a2530'}
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      )}
    </div>
  )
}
