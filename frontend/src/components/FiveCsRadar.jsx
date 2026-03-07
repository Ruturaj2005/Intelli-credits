/**
 * FiveCsRadar — Pentagon radar chart for the Five Cs of Credit.
 * Uses Recharts RadarChart.
 */
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

const C_LABELS = {
  character: 'Character',
  capacity: 'Capacity',
  capital: 'Capital',
  collateral: 'Collateral',
  conditions: 'Conditions',
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null
  const d = payload[0].payload
  return (
    <div className="card p-3 text-xs max-w-[220px]">
      <p className="font-syne font-bold text-[#00d4aa] mb-1">{d.c} — {d.score}/100</p>
      {d.reason && <p className="text-[#4a6070] leading-relaxed">{d.reason}</p>}
    </div>
  )
}

export default function FiveCsRadar({ scores = {} }) {
  const data = ['character', 'capacity', 'capital', 'collateral', 'conditions'].map((key) => {
    const c = scores[key] || {}
    return {
      c: C_LABELS[key],
      score: Number(c.score) || 0,
      reason: (c.reasons || [])[0] || '',
      fullMark: 100,
    }
  })

  return (
    <div className="w-full" style={{ height: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke="#1a2530" />
          <PolarAngleAxis
            dataKey="c"
            tick={{ fill: '#4a6070', fontSize: 11, fontFamily: 'Inter' }}
          />
          <Radar
            name="Score"
            dataKey="score"
            stroke="#00d4aa"
            fill="#00d4aa"
            fillOpacity={0.18}
            strokeWidth={2}
            dot={{ r: 4, fill: '#00d4aa', strokeWidth: 0 }}
            activeDot={{ r: 6, fill: '#00d4aa', stroke: '#020608', strokeWidth: 2 }}
          />
          <Tooltip content={<CustomTooltip />} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
