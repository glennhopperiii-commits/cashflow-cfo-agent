// Driver tornado from the sensitivity sweep: what moves week-13 covenant
// headroom, ranked. Green bars help the covenant, red bars hurt it, gray
// bars are the levers that do nothing (the teaching moment).

import { fmtM, fmtPct } from '../lib/format'

export default function DriverTornado({ sweep }) {
  if (!sweep?.length) return null

  const maxAbs = Math.max(...sweep.map((r) => Math.abs(r.delta_covenant_headroom)), 1)

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <h3 className="text-base font-bold text-slate-800 mb-1">Driver Tornado — Week-13 Headroom</h3>
      <p className="text-xs text-slate-400 mb-3">
        Change to covenant headroom per scenario · only flows crossing the week-13 boundary move it
      </p>
      <div className="space-y-2">
        {sweep.map((r) => {
          const v = r.delta_covenant_headroom
          const frac = Math.abs(v) / maxAbs
          const color = v > 0 ? 'bg-green-600' : v < 0 ? 'bg-red-600' : 'bg-slate-300'
          return (
            <div key={r.label} className="grid grid-cols-[minmax(0,2fr)_minmax(0,0.9fr)_auto] items-center gap-2">
              <span className="text-xs text-slate-600 leading-tight" title={r.label}>{r.label}</span>
              <div className="relative h-4 bg-slate-100 rounded overflow-hidden">
                <div className="absolute inset-y-0 left-1/2 w-px bg-slate-300" />
                {v >= 0 ? (
                  <div className={`absolute inset-y-0 left-1/2 ${color} rounded-r`} style={{ width: `${frac * 50}%` }} />
                ) : (
                  <div className={`absolute inset-y-0 ${color} rounded-l`} style={{ right: '50%', width: `${frac * 50}%` }} />
                )}
              </div>
              <span className={`text-xs font-mono tabular-nums w-32 text-right ${v > 0 ? 'text-green-700' : v < 0 ? 'text-red-700' : 'text-slate-400'}`}>
                {v === 0 ? 'no effect' : `${v > 0 ? '+' : '-'}${fmtM(Math.abs(v), 1).slice(1)}`}
                <span className="text-slate-400 ml-1">· {fmtPct(r.p_covenant_breach, 0)}</span>
              </span>
            </div>
          )
        })}
      </div>
      <p className="text-xs text-slate-400 mt-2">Right label: resulting P(breach) under each scenario.</p>
    </div>
  )
}
