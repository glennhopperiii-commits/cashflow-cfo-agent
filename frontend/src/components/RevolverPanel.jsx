// Weekly revolver utilization: drawn vs. undrawn availability against the
// $15M commitment. The climb from $6.0M to $12.0M is the LBO story in one bar chart.

import { fmtM } from '../lib/format'

const W = 420
const H = 220
const M = { top: 26, right: 12, bottom: 26, left: 44 }
const IW = W - M.left - M.right
const IH = H - M.top - M.bottom

export default function RevolverPanel({ det }) {
  if (!det?.weeks) return null
  const weeks = det.weeks
  const limit = weeks[0].revolver_balance + weeks[0].availability

  const bw = (IW / weeks.length) * 0.66
  const x = (i) => M.left + (i + 0.5) * (IW / weeks.length) - bw / 2
  const y = (v) => M.top + IH - (v / limit) * IH

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <h3 className="text-base font-bold text-slate-800 mb-1">Revolver Utilization</h3>
      <p className="text-xs text-slate-400 mb-2">
        Drawn vs. availability, {fmtM(limit, 0)} commitment · ends at {fmtM(weeks[12].revolver_balance, 1)} drawn
      </p>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        <line x1={M.left} x2={W - M.right} y1={y(limit)} y2={y(limit)} stroke="#DC2626" strokeWidth="1.5" strokeDasharray="5 4" />
        <text x={M.left} y={y(limit) - 5} fontSize="11" fontWeight="600" fill="#DC2626">Commitment {fmtM(limit, 0)}</text>

        {weeks.map((w, i) => (
          <g key={w.week}>
            {/* availability (light) on top of drawn (slate) */}
            <rect x={x(i)} y={y(limit)} width={bw} height={y(w.revolver_balance) - y(limit)} fill="#E2E8F0" />
            <rect x={x(i)} y={y(w.revolver_balance)} width={bw} height={M.top + IH - y(w.revolver_balance)} fill="#3B5998" />
            {w.revolver_draw > 0 && (
              <circle cx={x(i) + bw / 2} cy={y(w.revolver_balance) - 7} r="3" fill="#D97706" />
            )}
            <text x={x(i) + bw / 2} y={H - 8} textAnchor="middle" fontSize="10" fill="#64748B">{w.week}</text>
          </g>
        ))}

        {[0, 5_000_000, 10_000_000, 15_000_000].map((v) => (
          <text key={v} x={M.left - 6} y={y(v) + 4} textAnchor="end" fontSize="10" fill="#94A3B8" fontFamily="IBM Plex Mono, monospace">
            {fmtM(v, 0)}
          </text>
        ))}
      </svg>
      <p className="text-xs text-slate-400 mt-1">
        <span className="inline-block w-2.5 h-2.5 bg-[#3B5998] rounded-sm mr-1 align-middle" />drawn
        <span className="inline-block w-2.5 h-2.5 bg-slate-200 rounded-sm ml-3 mr-1 align-middle" />available
        <span className="inline-block w-2 h-2 bg-amber-500 rounded-full ml-3 mr-1 align-middle" />draw week
      </p>
    </div>
  )
}
