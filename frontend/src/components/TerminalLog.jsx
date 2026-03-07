/**
 * TerminalLog — dark terminal-style live log display.
 * Lines appear one-by-one via CSS animation.
 */
import { useEffect, useRef } from 'react'

const LEVEL_COLORS = {
  INFO:    '#4a6070',
  WARN:    '#ffd166',
  ERROR:   '#ef476f',
  SUCCESS: '#00d4aa',
}

const AGENT_COLORS = {
  INGESTOR:   '#0099ff',
  RESEARCH:   '#a78bfa',
  SCORER:     '#ffd166',
  CAM:        '#00d4aa',
  ARBITRATOR: '#ef476f',
  SYSTEM:     '#4a6070',
  ORCHESTRATOR: '#4a6070',
}

function LogLine({ entry, index }) {
  const agentColor = AGENT_COLORS[(entry.agent || '').toUpperCase()] || '#4a6070'
  const levelColor = LEVEL_COLORS[(entry.level || 'INFO').toUpperCase()] || '#4a6070'

  return (
    <div
      className="flex items-start gap-2 py-0.5 px-4 hover:bg-white/[0.02] transition-colors"
      style={{ animation: `fadeIn 0.2s ease ${Math.min(index * 30, 300)}ms both` }}
    >
      <span className="text-[#2a3a4a] font-mono text-[11px] shrink-0 mt-px">
        {entry.timestamp || '00:00:00'}
      </span>
      <span
        className="font-mono text-[11px] font-semibold shrink-0 mt-px uppercase tracking-wide"
        style={{ color: agentColor, minWidth: 80 }}
      >
        {(entry.agent || 'SYS').substring(0, 10)}
      </span>
      <span className="font-mono text-[11px] leading-relaxed" style={{ color: levelColor }}>
        {entry.message}
      </span>
    </div>
  )
}

export default function TerminalLog({ logs = [], maxHeight = 300, title = 'Live Agent Log' }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs.length])

  return (
    <div className="rounded-xl overflow-hidden border border-[#1a2530]">
      {/* Terminal title bar */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-[#0a0f12] border-b border-[#1a2530]">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-[#ef476f]/70" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#ffd166]/70" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#00d4aa]/70" />
        </div>
        <span className="text-[11px] text-[#4a6070] font-mono ml-2">{title}</span>
        <span className="ml-auto text-[10px] text-[#2a3a4a] font-mono">{logs.length} lines</span>
      </div>

      {/* Log lines */}
      <div
        className="overflow-y-auto py-2 bg-[#010508]"
        style={{ maxHeight, minHeight: 80 }}
      >
        {logs.length === 0 ? (
          <p className="text-center text-[#2a3a4a] font-mono text-[11px] py-6">
            Waiting for agent activity...
          </p>
        ) : (
          logs.map((entry, i) => (
            <LogLine key={i} entry={entry} index={i} />
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
