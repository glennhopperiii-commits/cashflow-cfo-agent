import { useState } from 'react'
import StatusBadge from './StatusBadge'
import { fmtUSD, fmtK, fmtM, fmtPct, fmtDelta } from '../lib/format'

const STEP_NUMBERS = {
  load_facility_and_position: 1,
  load_receivables: 2,
  load_payables_and_fixed: 3,
  build_deterministic_forecast: 4,
  run_monte_carlo: 5,
  run_scenario: 6,
  compute_variance: 7,
  draft_cash_narrative: 8,
  submit_for_review: 9,
  log_output: 10,
}

const STEP_DISPLAY = {
  load_facility_and_position: 'Position & Facility',
  load_receivables: 'Receivables',
  load_payables_and_fixed: 'Payables & Fixed Items',
  build_deterministic_forecast: 'Deterministic Forecast',
  run_monte_carlo: 'Monte Carlo',
  run_scenario: 'Sensitivity & Scenarios',
  compute_variance: 'Trailing Variance',
  draft_cash_narrative: 'Treasury Narrative',
  submit_for_review: 'Human Review Gate',
  log_output: 'Audit Trail',
}

const STEP_DESCRIPTIONS = {
  load_facility_and_position: 'Cash, revolver, floor, covenant, debt service',
  load_receivables: 'Open AR with observed payment behavior per customer',
  load_payables_and_fixed: 'AP by due week plus the fixed disbursement schedule',
  build_deterministic_forecast: '13-week roll-forward with revolver mechanics',
  run_monte_carlo: '1,000 resampled paths over timing and volume',
  run_scenario: 'What-ifs and the driver sweep on covenant headroom',
  compute_variance: 'Trailing 4-week forecast-vs-actual bridge',
  draft_cash_narrative: 'Sponsor commentary with a recommended action',
  submit_for_review: 'Human approves, edits, or rejects before anything ships',
  log_output: 'The complete decision trail, written to disk',
}

const BORDER_COLORS = {
  waiting: 'border-l-slate-300',
  running: 'border-l-amber-500',
  complete: 'border-l-green-600',
  'needs-review': 'border-l-amber-500',
}

const BG_COLORS = {
  waiting: '',
  running: 'bg-amber-50/50',
  complete: '',
  'needs-review': 'bg-amber-50/50',
}

function Row({ label, value, mono = true, bold = false, color = '' }) {
  return (
    <div className="flex justify-between text-sm py-0.5">
      <span className="text-slate-500">{label}</span>
      <span className={`${mono ? 'font-mono tabular-nums' : ''} ${bold ? 'font-bold' : ''} ${color || 'text-slate-800'}`}>{value}</span>
    </div>
  )
}

function FacilityDetail({ output }) {
  return (
    <div className="mt-3">
      <Row label="Beginning cash" value={fmtUSD(output.beginning_cash)} />
      <Row label="Revolver drawn / limit" value={`${fmtM(output.revolver.drawn, 1)} / ${fmtM(output.revolver.limit, 1)}`} />
      <Row label="Availability" value={fmtUSD(output.revolver.availability)} />
      <Row label="Beginning liquidity" value={fmtUSD(output.beginning_liquidity)} bold />
      <Row label="Operating cash floor" value={fmtUSD(output.operating_cash_floor)} color="text-amber-700" />
      <Row label={`Covenant (week ${output.covenant.test_week})`} value={`≥ ${fmtUSD(output.covenant.threshold)}`} color="text-red-700" />
      <Row label="Debt service, week 13" value={fmtUSD(output.term_loan.quarterly_amortization + output.term_loan.quarterly_interest)} />
    </div>
  )
}

function ReceivablesDetail({ output }) {
  const top = output.customers?.slice(0, 6) || []
  return (
    <div className="mt-3">
      <Row label="Open AR" value={fmtUSD(output.total_open_ar)} bold />
      <Row label="Invoices / top-5 share" value={`${output.invoice_count} / ${fmtPct(output.top5_concentration, 0)}`} />
      <div className="mt-2 border border-slate-200 rounded overflow-hidden">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="bg-[#3B5998] text-white">
              <th className="px-2 py-1.5 text-left font-semibold">Customer</th>
              <th className="px-2 py-1.5 text-right font-semibold">Open AR</th>
              <th className="px-2 py-1.5 text-right font-semibold">Terms</th>
              <th className="px-2 py-1.5 text-right font-semibold">Pays in</th>
            </tr>
          </thead>
          <tbody>
            {top.map((c, i) => (
              <tr key={c.customer} className={i % 2 === 1 ? 'bg-slate-50' : 'bg-white'}>
                <td className="px-2 py-1 text-slate-800">
                  {c.customer}
                  {c.term_stretch_flag && <span className="text-amber-600 font-bold ml-1" title={`${c.stretch_days_vs_terms} days past terms`}>⚑</span>}
                </td>
                <td className="px-2 py-1 text-right font-mono tabular-nums">{fmtK(c.open_ar)}</td>
                <td className="px-2 py-1 text-right text-slate-500">{c.terms}</td>
                <td className={`px-2 py-1 text-right font-mono tabular-nums ${c.term_stretch_flag ? 'text-amber-700 font-bold' : ''}`}>
                  {Math.round(c.days_to_pay)}d
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {output.flagged_term_stretch?.length > 0 && (
        <p className="text-xs text-amber-700 mt-2">
          ⚑ Payment behavior well past stated terms: {output.flagged_term_stretch.join(', ')}
        </p>
      )}
    </div>
  )
}

function PayablesDetail({ output }) {
  return (
    <div className="mt-3">
      <Row label="Open AP" value={fmtUSD(output.total_open_ap)} bold />
      <Row label="Bills" value={output.ap_bill_count} />
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mt-3 mb-1">One-time outflows</p>
      {output.one_time_items?.map((item) => (
        <Row key={`${item.week}-${item.item}`} label={`Wk ${item.week} · ${item.item.split(':')[0].split('(')[0].trim()}`} value={fmtK(item.amount)} />
      ))}
      <p className="text-xs text-slate-400 mt-2">
        {output.discretionary_items?.length || 0} discretionary (deferrable) items flagged
      </p>
    </div>
  )
}

function DeterministicDetail({ output }) {
  return (
    <div className="mt-3">
      <div className="flex gap-2 mb-3">
        <span className="px-2.5 py-1 rounded bg-amber-50 text-amber-800 text-sm font-semibold">
          Trough {fmtM(output.trough_cash, 2)} · wk {output.trough_week}
        </span>
        <span className={`px-2.5 py-1 rounded text-sm font-semibold ${output.covenant_pass ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {output.covenant_pass ? 'PASS' : 'BREACH'} · headroom {fmtM(output.covenant_headroom, 2)}
        </span>
      </div>
      <div className="border border-slate-200 rounded overflow-hidden">
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="bg-[#3B5998] text-white">
              <th className="px-2 py-1.5 text-left font-semibold">Wk</th>
              <th className="px-2 py-1.5 text-right font-semibold">Receipts</th>
              <th className="px-2 py-1.5 text-right font-semibold">Disb</th>
              <th className="px-2 py-1.5 text-right font-semibold">Draw</th>
              <th className="px-2 py-1.5 text-right font-semibold">Cash</th>
              <th className="px-2 py-1.5 text-right font-semibold">Liquidity</th>
            </tr>
          </thead>
          <tbody>
            {output.weeks?.map((w, i) => (
              <tr key={w.week} className={`${w.week === output.trough_week ? 'bg-amber-50 font-bold' : i % 2 === 1 ? 'bg-slate-50' : 'bg-white'}`}>
                <td className="px-2 py-0.5">{w.week}</td>
                <td className="px-2 py-0.5 text-right font-mono tabular-nums">{fmtK(w.receipts)}</td>
                <td className="px-2 py-0.5 text-right font-mono tabular-nums">{fmtK(w.disbursements)}</td>
                <td className="px-2 py-0.5 text-right font-mono tabular-nums text-amber-700">{w.revolver_draw ? fmtK(w.revolver_draw) : ''}</td>
                <td className="px-2 py-0.5 text-right font-mono tabular-nums">{fmtK(w.ending_cash)}</td>
                <td className="px-2 py-0.5 text-right font-mono tabular-nums">{fmtK(w.covenant_liquidity)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function MonteCarloDetail({ output }) {
  return (
    <div className="mt-3">
      <Row label="Iterations (seeded)" value={`${output.iterations?.toLocaleString()} · seed ${output.seed}`} />
      <Row label="P(covenant breach, wk 13)" value={fmtPct(output.p_covenant_breach, 1)} bold color="text-red-700" />
      <Row label="P(floor unrestorable)" value={fmtPct(output.p_below_floor_any_week, 1)} color="text-green-700" />
      <Row label="Wk-13 liquidity P10 / P50 / P90"
           value={`${fmtM(output.test_week_liquidity_p10, 2)} / ${fmtM(output.test_week_liquidity_p50, 2)} / ${fmtM(output.test_week_liquidity_p90, 2)}`} />
      <Row label="Trough cash P10 / P50 / P90"
           value={`${fmtM(output.trough_cash_p10, 2)} / ${fmtM(output.trough_cash_p50, 2)} / ${fmtM(output.trough_cash_p90, 2)}`} />
      <p className="text-xs text-slate-500 mt-2">
        The P10 path breaches the covenant that the single-point forecast clears.
      </p>
    </div>
  )
}

function ScenarioDetail({ outputs }) {
  const [active, setActive] = useState(0)
  if (!outputs?.length) return null

  return (
    <div className="mt-3">
      <div className="flex gap-1 flex-wrap border-b border-slate-200 mb-3">
        {outputs.map((o, i) => (
          <button
            key={i}
            onClick={() => setActive(i)}
            className={`px-2.5 py-1.5 text-xs font-medium rounded-t transition-colors
              ${active === i ? 'bg-white border border-b-white border-slate-200 text-[#3B5998] -mb-px' : 'text-slate-500 hover:text-slate-700'}`}
          >
            {o.sweep ? 'Driver sweep' : (o.scenario?.scenario_type || `Scenario ${i + 1}`)}
          </button>
        ))}
      </div>
      {outputs[active]?.sweep ? (
        <div className="space-y-1">
          {outputs[active].sweep.map((r) => (
            <div key={r.label} className="flex justify-between text-[13px] gap-2">
              <span className="text-slate-600 truncate">{r.label}</span>
              <span className={`font-mono tabular-nums shrink-0 ${r.delta_covenant_headroom > 0 ? 'text-green-700' : r.delta_covenant_headroom < 0 ? 'text-red-700' : 'text-slate-400'}`}>
                {fmtDelta(r.delta_covenant_headroom)} · {fmtPct(r.p_covenant_breach, 0)}
              </span>
            </div>
          ))}
        </div>
      ) : outputs[active]?.result ? (
        <div>
          <Row label="Δ headroom" value={fmtDelta(outputs[active].result.delta_covenant_headroom)}
               color={outputs[active].result.delta_covenant_headroom >= 0 ? 'text-green-700' : 'text-red-700'} bold />
          <Row label="Δ trough" value={fmtDelta(outputs[active].result.delta_trough_cash)} />
          <Row label="P(breach) after" value={fmtPct(outputs[active].result.p_covenant_breach, 1)} />
        </div>
      ) : (
        <p className="text-sm text-red-600">{outputs[active]?.error}</p>
      )}
    </div>
  )
}

function VarianceDetail({ output }) {
  return (
    <div className="mt-3">
      <Row label="Forecast vs. actual collections"
           value={`${fmtK(output.forecast_collections_total)} → ${fmtK(output.actual_collections_total)}`} />
      <Row label="Miss" value={`${fmtUSD(output.total_variance)} (${fmtPct(output.variance_pct_of_forecast, 1)})`} bold color="text-red-700" />
      <Row label="Vantage timing" value={`${fmtUSD(output.attribution.vantage_timing)} (${fmtPct(output.attribution.vantage_share_of_miss, 0)} of miss)`} />
      <Row label="All other (volume)" value={fmtUSD(output.attribution.all_other)} />
      <p className="text-xs text-slate-500 mt-2">Timing on a collectible receivable, not volume loss.</p>
    </div>
  )
}

const ACTION_BADGE = {
  approved: { bg: 'bg-green-50', text: 'text-green-700', label: 'Approved' },
  edited: { bg: 'bg-amber-50', text: 'text-amber-700', label: 'Edited' },
  rejected: { bg: 'bg-red-50', text: 'text-red-700', label: 'Rejected' },
}

function ReviewDetail({ output, reviewSections }) {
  const decisions = output?.decisions || []
  const decisionMap = Object.fromEntries(decisions.map((d) => [d.section_title, d]))
  const ra = output?.recommended_action_disposition

  return (
    <div className="mt-3 space-y-3">
      {ra && (
        <div className={`border rounded-lg p-3 ${ra.disposition === 'approved' ? 'border-green-300 bg-green-50/50' : 'border-red-300 bg-red-50/50'}`}>
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500 mb-1">Recommended action · {ra.disposition}</p>
          <p className="text-sm text-slate-700">{ra.action}</p>
        </div>
      )}
      {(reviewSections || []).map((section, i) => {
        const decision = decisionMap[section.title]
        const badge = decision ? (ACTION_BADGE[decision.action] || ACTION_BADGE.approved) : null
        return (
          <div key={i} className="border border-slate-200 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 bg-slate-50 border-b border-slate-200">
              <h4 className="text-sm font-semibold text-slate-800">{section.title}</h4>
              {badge && (
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${badge.bg} ${badge.text}`}>{badge.label}</span>
              )}
            </div>
            <div className="px-3 py-2">
              <p className="text-[13px] text-slate-700 leading-relaxed whitespace-pre-line line-clamp-4">
                {decision?.edited_content || section.content}
              </p>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default function StepCard({ stepName, status, output, reviewSections }) {
  const [manualToggle, setManualToggle] = useState(null)
  const hasOutput = status === 'complete' || status === 'needs-review'
  const canExpand = hasOutput && output
  const expanded = manualToggle !== null ? manualToggle : false

  return (
    <div className={`bg-white rounded-lg border border-slate-200 border-l-4 ${BORDER_COLORS[status]} ${BG_COLORS[status]} transition-all`}>
      <button
        onClick={() => canExpand && setManualToggle(!expanded)}
        className={`w-full px-5 py-4 flex items-center justify-between text-left ${canExpand ? 'cursor-pointer' : 'cursor-default'}`}
      >
        <div className="flex items-center gap-3">
          <span className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-base font-semibold text-slate-600 shrink-0">
            {STEP_NUMBERS[stepName]}
          </span>
          <div>
            <span className="font-semibold text-lg text-slate-800 block">{STEP_DISPLAY[stepName]}</span>
            <span className="text-xs text-slate-400 block mt-0.5">{STEP_DESCRIPTIONS[stepName]}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={status} />
          {canExpand && (
            <svg className={`w-4 h-4 text-slate-400 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          )}
        </div>
      </button>

      {expanded && canExpand && (
        <div className="px-4 pb-4 border-t border-slate-100">
          {stepName === 'load_facility_and_position' && <FacilityDetail output={output} />}
          {stepName === 'load_receivables' && <ReceivablesDetail output={output} />}
          {stepName === 'load_payables_and_fixed' && <PayablesDetail output={output} />}
          {stepName === 'build_deterministic_forecast' && <DeterministicDetail output={output} />}
          {stepName === 'run_monte_carlo' && <MonteCarloDetail output={output} />}
          {stepName === 'run_scenario' && <ScenarioDetail outputs={output} />}
          {stepName === 'compute_variance' && <VarianceDetail output={output} />}
          {stepName === 'draft_cash_narrative' && (
            <div className="mt-3 text-sm text-slate-600">
              {output.section_count} sections drafted: {output.section_titles?.join(', ')}.
              <span className="block mt-1 text-slate-500">Full draft appears in the Review Workspace.</span>
            </div>
          )}
          {stepName === 'submit_for_review' && <ReviewDetail output={output} reviewSections={reviewSections} />}
          {stepName === 'log_output' && (
            <div className="mt-3 text-sm text-slate-600">
              Audit trail written: {output.entry_count} sections logged
              <span className="block font-mono text-xs text-slate-400 mt-1">{output.path}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
