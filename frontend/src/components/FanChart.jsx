// The money-shot chart: 13 weeks of ending cash and covenant liquidity with
// the operating floor and covenant threshold lines, event markers, and the
// deterministic <-> probabilistic toggle. Probabilistic mode overlays the
// P10-P90 fan and the breach-probability callout. Transitions are loud on
// purpose (color and shape, not subtle opacity) so they read on a recording.

import { fmtM, fmtPct } from '../lib/format'

const W = 860
const H = 400
const M = { top: 24, right: 30, bottom: 54, left: 64 }
const IW = W - M.left - M.right
const IH = H - M.top - M.bottom

const INK = '#1E293B'
const SLATE = '#3B5998'
const AMBER = '#D97706'
const RED = '#DC2626'
const GRID = '#E2E8F0'

const EVENT_MARKERS = [
  { week: 5, label: 'Insurance $450K' },
  { week: 6, label: 'Capex $800K' },
  { week: 7, label: 'Vantage $2.1M in' },
  { week: 9, label: 'Earn-out $1.0M' },
  { week: 13, label: 'Debt svc $2.2M' },
]

function linePath(xs, ys) {
  return xs.map((x, i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${ys[i].toFixed(1)}`).join(' ')
}

function bandPath(xs, upper, lower) {
  const fwd = xs.map((x, i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${upper[i].toFixed(1)}`).join(' ')
  const rev = [...xs].reverse().map((x, i) => `L${x.toFixed(1)},${lower[lower.length - 1 - i].toFixed(1)}`).join(' ')
  return `${fwd} ${rev} Z`
}

export default function FanChart({ det, mc, mode }) {
  if (!det?.weeks) return null

  const weeks = det.weeks.map((w) => w.week)
  const cash = det.weeks.map((w) => w.ending_cash)
  const liq = det.weeks.map((w) => w.covenant_liquidity)
  const floor = 1_500_000
  const threshold = det.covenant_threshold ?? 4_000_000
  const probabilistic = mode === 'probabilistic' && mc

  const yMax = Math.max(...liq, ...(probabilistic ? mc.liquidity_p90 : []), threshold) * 1.08
  const x = (week) => M.left + ((week - 1) / (weeks.length - 1)) * IW
  const y = (v) => M.top + IH - (v / yMax) * IH
  const xs = weeks.map(x)

  const yTicks = []
  for (let v = 0; v <= yMax; v += 2_000_000) yTicks.push(v)

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="13-week cash and covenant liquidity chart">
      {/* grid + y axis */}
      {yTicks.map((v) => (
        <g key={v}>
          <line x1={M.left} x2={W - M.right} y1={y(v)} y2={y(v)} stroke={GRID} strokeWidth="1" />
          <text x={M.left - 8} y={y(v) + 4} textAnchor="end" fontSize="12" fill="#64748B" fontFamily="IBM Plex Mono, monospace">
            {fmtM(v, 0)}
          </text>
        </g>
      ))}

      {/* x axis week labels */}
      {weeks.map((w, i) => (
        <text key={w} x={xs[i]} y={H - M.bottom + 18} textAnchor="middle" fontSize="12" fill="#64748B">
          W{w}
        </text>
      ))}

      {/* event markers */}
      {EVENT_MARKERS.map((m, i) => (
        <g key={m.week}>
          <line x1={x(m.week)} x2={x(m.week)} y1={M.top} y2={M.top + IH} stroke="#CBD5E1" strokeWidth="1" strokeDasharray="2 4" />
          <text
            x={x(m.week)} y={H - M.bottom + (i % 2 === 0 ? 32 : 44)}
            textAnchor="middle" fontSize="10" fill="#94A3B8"
          >
            {m.label}
          </text>
        </g>
      ))}

      {/* threshold lines */}
      <line x1={M.left} x2={W - M.right} y1={y(threshold)} y2={y(threshold)} stroke={RED} strokeWidth="2" strokeDasharray="6 4" />
      <text x={M.left + 6} y={y(threshold) - 6} fontSize="12" fontWeight="700" fill={RED}>
        Covenant threshold {fmtM(threshold, 1)} (liquidity)
      </text>
      <line x1={M.left} x2={W - M.right} y1={y(floor)} y2={y(floor)} stroke={AMBER} strokeWidth="2" strokeDasharray="6 4" />
      <text x={M.left + 6} y={y(floor) + 16} fontSize="12" fontWeight="700" fill={AMBER}>
        Operating floor {fmtM(floor, 1)} (cash)
      </text>

      {/* probabilistic fans */}
      {mc && (
        <g style={{ opacity: probabilistic ? 1 : 0, transition: 'opacity 500ms ease' }}>
          <path d={bandPath(xs, mc.liquidity_p90.map(y), mc.liquidity_p10.map(y))} fill={SLATE} fillOpacity="0.22" />
          <path d={linePath(xs, mc.liquidity_p50.map(y))} fill="none" stroke={SLATE} strokeWidth="3" />
          <path d={bandPath(xs, mc.ending_cash_p90.map(y), mc.ending_cash_p10.map(y))} fill={AMBER} fillOpacity="0.22" />
          <path d={linePath(xs, mc.ending_cash_p50.map(y))} fill="none" stroke={AMBER} strokeWidth="2.5" />
        </g>
      )}

      {/* deterministic lines: solid + dotted markers in D mode, thin dashed ghost in P mode */}
      <g>
        <path
          d={linePath(xs, liq.map(y))}
          fill="none"
          stroke={probabilistic ? '#94A3B8' : SLATE}
          strokeWidth={probabilistic ? 1.5 : 3.5}
          strokeDasharray={probabilistic ? '5 4' : 'none'}
          style={{ transition: 'stroke 400ms ease, stroke-width 400ms ease' }}
        />
        <path
          d={linePath(xs, cash.map(y))}
          fill="none"
          stroke={probabilistic ? '#CBD5E1' : INK}
          strokeWidth={probabilistic ? 1.5 : 3}
          strokeDasharray={probabilistic ? '5 4' : 'none'}
          style={{ transition: 'stroke 400ms ease, stroke-width 400ms ease' }}
        />
        {!probabilistic && weeks.map((w, i) => (
          <g key={w}>
            <circle cx={xs[i]} cy={y(liq[i])} r="4" fill={SLATE} />
            <circle cx={xs[i]} cy={y(cash[i])} r="3.5" fill={INK} />
          </g>
        ))}
      </g>

      {/* series labels */}
      <text x={xs[2]} y={y(liq[2]) - 12} fontSize="13" fontWeight="700" fill={probabilistic ? SLATE : SLATE}>
        Covenant liquidity (cash + availability)
      </text>
      <text x={xs[2]} y={y(cash[2]) - 10} fontSize="13" fontWeight="700" fill={probabilistic ? AMBER : INK}>
        Ending cash
      </text>

      {/* breach callout, probabilistic mode only: parked in the clear space
          between the covenant line and the cash band, pointing at W13 */}
      {mc && (
        <g style={{ opacity: probabilistic ? 1 : 0, transition: 'opacity 500ms ease 150ms' }}>
          <line
            x1={x(12.05)} y1={y(3_050_000)} x2={x(13)} y2={y(mc.liquidity_p10[12]) + 4}
            stroke={RED} strokeWidth="1.5" strokeDasharray="3 3"
          />
          <rect
            x={x(9.55)} y={y(3_450_000)}
            width="196" height="52" rx="8"
            fill="#FEF2F2" stroke={RED} strokeWidth="1.5"
          />
          <text x={x(9.55) + 12} y={y(3_450_000) + 21} fontSize="15" fontWeight="700" fill={RED}>
            P(breach at week 13)
          </text>
          <text x={x(9.55) + 12} y={y(3_450_000) + 44} fontSize="20" fontWeight="700" fill={RED} fontFamily="IBM Plex Mono, monospace">
            {fmtPct(mc.p_covenant_breach, 1)}
          </text>
        </g>
      )}
    </svg>
  )
}
