/**
 * RedFlagCard — displays a single risk flag with severity badge.
 */

const SEVERITY_STYLES = {
  HIGH: {
    bg: 'bg-[#ef476f]/10',
    border: 'border-[#ef476f]/30',
    badge: 'badge-reject',
    icon: '🔴',
  },
  MEDIUM: {
    bg: 'bg-[#ffd166]/10',
    border: 'border-[#ffd166]/30',
    badge: 'badge-conditional',
    icon: '🟡',
  },
  LOW: {
    bg: 'bg-[#4a6070]/10',
    border: 'border-[#4a6070]/30',
    badge: 'badge-pending',
    icon: '🟢',
  },
}

function detectSeverity(flag) {
  const f = flag.toLowerCase()
  if (f.includes('high') || f.includes('fraud') || f.includes('npa') ||
      f.includes('nclt') || f.includes('auto-reject')) return 'HIGH'
  if (f.includes('medium') || f.includes('discrepancy') || f.includes('caution')) return 'MEDIUM'
  return 'LOW'
}

export default function RedFlagCard({ flag, severity, source, index }) {
  const sev = (severity || detectSeverity(flag || '')).toUpperCase()
  const styles = SEVERITY_STYLES[sev] || SEVERITY_STYLES.LOW

  return (
    <div
      className={`card border rounded-lg p-4 animate-slide-up ${styles.bg} ${styles.border}`}
      style={{ animationDelay: `${(index || 0) * 60}ms` }}
    >
      <div className="flex items-start gap-3">
        <span className="text-base mt-0.5">{styles.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <span className={`badge ${styles.badge}`}>{sev}</span>
            {source && (
              <a
                href={source}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[10px] text-[#0099ff] hover:underline truncate max-w-[180px]"
              >
                {source.replace(/^https?:\/\//, '').split('/')[0]}
              </a>
            )}
          </div>
          <p className="text-xs text-[#e8f0f5] leading-relaxed">{flag}</p>
        </div>
      </div>
    </div>
  )
}
