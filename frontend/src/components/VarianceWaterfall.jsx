// Trailing 4-week actual-vs-forecast bridge: forecast collections, the Vantage
// timing slip, other volume noise, actual collections. Timing vs. volume in
// one picture.

import { fmtK, fmtPct } from '../lib/format'

const W = 420
const H = 230
const M = { top: 30, right: 16, bottom: 44, left: 16 }
const IW = W - M.left - M.right
const IH = H - M.top - M.bottom

export default function VarianceWaterfall({ variance }) {
  if (!variance) return null

  const forecast = variance.forecast_collections_total
  const vantage = variance.attribution.vantage_timing
  const other = variance.attribution.all_other
  const actual = variance.actual_collections_total

  const bars = [
    { label: 'Prior forecast', from: 0, to: forecast, color: '#3B5998', abs: true },
    { label: 'Vantage timing', from: forecast, to: forecast + vantage, color: '#DC2626' },
    { label: 'Other (volume)', from: forecast + vantage, to: forecast + vantage + other, color: '#D97706' },
    { label: 'Actual', from: 0, to: actual, color: '#1E293B', abs: true },
  ]

  const yMax = forecast * 1.06
  const yMin = actual * 0.92
  const y = (v) => M.top + IH - ((v - yMin) / (yMax - yMin)) * IH
  const bw = (IW / bars.length) * 0.56
  const x = (i) => M.left + (i + 0.5) * (IW / bars.length) - bw / 2

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <h3 className="text-base font-bold text-slate-800 mb-1">Trailing 4-Week Variance</h3>
      <p className="text-xs text-slate-400 mb-2">
        Collections {fmtPct(variance.variance_pct_of_forecast, 1)} vs. forecast ·
        Vantage timing is {fmtPct(variance.attribution.vantage_share_of_miss, 0)} of the miss
      </p>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        {bars.map((b, i) => {
          const top = Math.min(y(b.abs ? b.to : Math.max(b.from, b.to)), y(yMin))
          const bottom = b.abs ? y(yMin) : y(Math.min(b.from, b.to))
          const height = Math.max(bottom - top, 2)
          const delta = b.to - b.from
          return (
            <g key={b.label}>
              {i > 0 && !b.abs && (
                <line
                  x1={x(i - 1) + bw} y1={y(b.from)} x2={x(i)} y2={y(b.from)}
                  stroke="#CBD5E1" strokeWidth="1" strokeDasharray="3 3"
                />
              )}
              <rect x={x(i)} y={top} width={bw} height={height} fill={b.color} fillOpacity={b.abs ? 1 : 0.85} rx="2" />
              <text x={x(i) + bw / 2} y={top - 6} textAnchor="middle" fontSize="11" fontWeight="700"
                    fill={b.color} fontFamily="IBM Plex Mono, monospace">
                {b.abs ? fmtK(b.to) : fmtK(delta)}
              </text>
              <text x={x(i) + bw / 2} y={H - 24} textAnchor="middle" fontSize="10.5" fill="#64748B">
                {b.label.split(' ')[0]}
              </text>
              <text x={x(i) + bw / 2} y={H - 12} textAnchor="middle" fontSize="10.5" fill="#64748B">
                {b.label.split(' ').slice(1).join(' ')}
              </text>
            </g>
          )
        })}
      </svg>
      <p className="text-xs text-slate-500 mt-1">
        The slipped Vantage invoice is timing on a collectible receivable, not volume loss.
      </p>
    </div>
  )
}
