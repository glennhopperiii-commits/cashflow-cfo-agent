// The main visualization panel. Charts light up as the agent produces the
// data behind them. The deterministic <-> probabilistic toggle is the single
// most important interaction in the demo.

import { useState } from 'react'
import FanChart from './FanChart'
import RevolverPanel from './RevolverPanel'
import CovenantGauge from './CovenantGauge'
import VarianceWaterfall from './VarianceWaterfall'
import DriverTornado from './DriverTornado'
import { fmtM, fmtPct } from '../lib/format'

function ModeToggle({ mode, setMode, mcReady }) {
  return (
    <div className="inline-flex rounded-lg border-2 border-slate-300 overflow-hidden">
      <button
        onClick={() => setMode('deterministic')}
        className={`px-4 py-2 text-sm font-bold transition-colors ${
          mode === 'deterministic'
            ? 'bg-slate-800 text-white'
            : 'bg-white text-slate-500 hover:bg-slate-50'
        }`}
      >
        Deterministic
      </button>
      <button
        onClick={() => mcReady && setMode('probabilistic')}
        disabled={!mcReady}
        className={`px-4 py-2 text-sm font-bold transition-colors ${
          mode === 'probabilistic'
            ? 'bg-[#3B5998] text-white'
            : mcReady
              ? 'bg-white text-slate-500 hover:bg-slate-50'
              : 'bg-white text-slate-300 cursor-not-allowed'
        }`}
        title={mcReady ? '' : 'Runs after the Monte Carlo step'}
      >
        Probabilistic
      </button>
    </div>
  )
}

export default function ForecastDashboard({ det, mc, scenarios, variance }) {
  const [mode, setMode] = useState('deterministic')
  const sweep = scenarios?.find((s) => s?.sweep)?.sweep

  if (!det) return null

  const probabilistic = mode === 'probabilistic' && mc

  return (
    <div className="space-y-4">
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="flex items-start justify-between gap-4 mb-2">
          <div>
            <h3 className="text-lg font-bold text-slate-800">13-Week Cash Forecast</h3>
            <p className="text-sm text-slate-500">
              {probabilistic ? (
                <>P10–P90 fan over 1,000 iterations · deterministic path shown dashed ·{' '}
                  <span className="font-bold text-red-600">P(breach) {fmtPct(mc.p_covenant_breach, 1)}</span></>
              ) : (
                <>Single-point path · trough {fmtM(det.trough_cash, 2)} in week {det.trough_week} ·
                  week-13 headroom <span className="font-bold text-green-700">{fmtM(det.covenant_headroom, 2)}</span></>
              )}
            </p>
          </div>
          <ModeToggle mode={mode} setMode={setMode} mcReady={!!mc} />
        </div>
        <FanChart det={det} mc={mc} mode={mode} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <RevolverPanel det={det} />
        <CovenantGauge det={det} mc={mc} mode={mode} />
      </div>

      {(variance || sweep) && (
        <div className="grid grid-cols-2 gap-4">
          {variance ? <VarianceWaterfall variance={variance} /> : <div />}
          {sweep ? <DriverTornado sweep={sweep} /> : <div />}
        </div>
      )}
    </div>
  )
}
