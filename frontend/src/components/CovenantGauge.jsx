// Week-13 covenant headroom gauge. Deterministic mode: needle at the test-week
// liquidity vs. the $4.0M threshold. Probabilistic mode: the same gauge with
// the P10-P90 span shaded and the breach probability front and center.

import { fmtM, fmtPct } from '../lib/format'

const W = 420
const H = 220
const CX = W / 2
const CY = 178
const R = 128

function polar(angleDeg, r = R) {
  const rad = (Math.PI * angleDeg) / 180
  return [CX + r * Math.cos(rad), CY - r * Math.sin(rad)]
}

// Map liquidity dollars onto the 180deg..0deg arc
function angleFor(v, maxV) {
  const t = Math.max(0, Math.min(1, v / maxV))
  return 180 - t * 180
}

function arcPath(a1, a2, r = R) {
  const [x1, y1] = polar(a1, r)
  const [x2, y2] = polar(a2, r)
  const large = Math.abs(a1 - a2) > 180 ? 1 : 0
  return `M${x1.toFixed(1)},${y1.toFixed(1)} A${r},${r} 0 ${large} 1 ${x2.toFixed(1)},${y2.toFixed(1)}`
}

export default function CovenantGauge({ det, mc, mode }) {
  if (!det) return null
  const threshold = det.covenant_threshold ?? 4_000_000
  const value = det.test_week_liquidity
  const maxV = 8_000_000
  const probabilistic = mode === 'probabilistic' && mc

  const breach = probabilistic ? mc.p_covenant_breach : null

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <h3 className="text-base font-bold text-slate-800 mb-1">Week-13 Covenant Test</h3>
      <p className="text-xs text-slate-400 mb-2">
        Liquidity vs. {fmtM(threshold, 1)} minimum · headroom {fmtM(det.covenant_headroom, 2)}
      </p>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        {/* track: red below threshold, slate above */}
        <path d={arcPath(180, angleFor(threshold, maxV))} fill="none" stroke="#FECACA" strokeWidth="20" strokeLinecap="butt" />
        <path d={arcPath(angleFor(threshold, maxV), 0)} fill="none" stroke="#E2E8F0" strokeWidth="20" strokeLinecap="butt" />

        {/* P10-P90 span in probabilistic mode */}
        {probabilistic && (
          <path
            d={arcPath(angleFor(mc.test_week_liquidity_p10, maxV), angleFor(mc.test_week_liquidity_p90, maxV))}
            fill="none" stroke="#3B5998" strokeOpacity="0.35" strokeWidth="20"
            style={{ transition: 'opacity 400ms' }}
          />
        )}

        {/* threshold tick */}
        <line
          x1={polar(angleFor(threshold, maxV), R - 16)[0]} y1={polar(angleFor(threshold, maxV), R - 16)[1]}
          x2={polar(angleFor(threshold, maxV), R + 16)[0]} y2={polar(angleFor(threshold, maxV), R + 16)[1]}
          stroke="#DC2626" strokeWidth="3"
        />
        <text x={polar(angleFor(threshold, maxV), R + 30)[0]} y={polar(angleFor(threshold, maxV), R + 30)[1]} textAnchor="middle" fontSize="11" fontWeight="700" fill="#DC2626">
          {fmtM(threshold, 0)}
        </text>

        {/* needle at deterministic test-week liquidity */}
        <line
          x1={CX} y1={CY}
          x2={polar(angleFor(value, maxV), R - 26)[0]} y2={polar(angleFor(value, maxV), R - 26)[1]}
          stroke="#1E293B" strokeWidth="3.5" strokeLinecap="round"
        />
        <circle cx={CX} cy={CY} r="6" fill="#1E293B" />

        {/* center readout */}
        {probabilistic ? (
          <g>
            <text x={CX} y={CY - 52} textAnchor="middle" fontSize="15" fontWeight="700" fill="#DC2626">P(breach)</text>
            <text x={CX} y={CY - 24} textAnchor="middle" fontSize="30" fontWeight="700" fill="#DC2626" fontFamily="IBM Plex Mono, monospace">
              {fmtPct(breach, 1)}
            </text>
          </g>
        ) : (
          <g>
            <text x={CX} y={CY - 52} textAnchor="middle" fontSize="14" fontWeight="600" fill="#64748B">liquidity</text>
            <text x={CX} y={CY - 24} textAnchor="middle" fontSize="28" fontWeight="700" fill={det.covenant_pass ? '#16A34A' : '#DC2626'} fontFamily="IBM Plex Mono, monospace">
              {fmtM(value, 2)}
            </text>
          </g>
        )}

        <text x={M_LEFT_LABEL_X} y={CY + 16} fontSize="11" fill="#94A3B8">$0</text>
        <text x={W - 40} y={CY + 16} fontSize="11" fill="#94A3B8">{fmtM(maxV, 0)}</text>
      </svg>
    </div>
  )
}

const M_LEFT_LABEL_X = CX - R - 8
