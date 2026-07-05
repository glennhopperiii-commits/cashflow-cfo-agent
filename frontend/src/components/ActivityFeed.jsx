import { useEffect, useRef } from 'react'
import { fmtM, fmtPct } from '../lib/format'

const STEP_NARRATION = {
  load_facility_and_position: {
    started: 'The agent starts where every treasury conversation starts: the position. Beginning cash, what is drawn on the revolver, what availability remains, the operating floor policy, and the covenant that gets certified to the lender at quarter end.',
    completed: (o) =>
      `Position loaded: ${fmtM(o?.beginning_cash, 1)} cash, ${fmtM(o?.revolver?.drawn, 1)} drawn on the ${fmtM(o?.revolver?.limit, 1)} revolver, ${fmtM(o?.beginning_liquidity, 1)} of beginning liquidity against a ${fmtM(o?.covenant?.threshold, 1)} week-13 covenant.`,
  },
  load_receivables: {
    started: 'Loading open AR with each customer\'s observed payment behavior, not just stated terms. The gap between the two is where collection forecasts go wrong.',
    completed: (o) =>
      `${fmtM(o?.total_open_ar, 1)} of open AR across ${o?.invoice_count} invoices. Top 5 customers are ${Math.round((o?.top5_concentration || 0) * 100)}% of the book. Flagged for term stretch: ${(o?.flagged_term_stretch || []).join(', ') || 'none'}.`,
  },
  load_payables_and_fixed: {
    started: 'Loading the disbursement side: open AP by due week, biweekly payroll, rent, benefits, forecast ramp material purchases, and the one-time items a naive forecast misses.',
    completed: (o) =>
      `${fmtM(o?.total_open_ap, 1)} of open AP across ${o?.ap_bill_count} bills, heaviest weeks 3-7 from the aerospace ramp. ${o?.one_time_items?.length || 0} scheduled one-timers including week-13 debt service.`,
  },
  build_deterministic_forecast: {
    started: 'Rolling 13 weeks forward: beginning cash plus receipts minus disbursements, with the revolver auto-drawing to defend the $1.5M floor and sweeping down when cash runs above the buffer.',
    completed: (o) =>
      `Deterministic path: cash troughs at ${fmtM(o?.trough_cash, 2)} in week ${o?.trough_week}, and week-13 liquidity lands at ${fmtM(o?.test_week_liquidity, 2)} against the ${fmtM(o?.covenant_threshold, 1)} covenant — a ${o?.covenant_pass ? 'PASS' : 'BREACH'} with ${fmtM(o?.covenant_headroom, 2)} of headroom. Watch what the next step does to that comfort.`,
  },
  run_monte_carlo: {
    started: 'Now the same engine runs a thousand times. Each pass resamples when customers actually pay (from their measured behavior) and what the ramp actually bills. The single line becomes a distribution.',
    completed: (o) =>
      `This is the turn: P(covenant breach at week 13) = ${fmtPct(o?.p_covenant_breach, 1)}. The P10 path ends at ${fmtM(o?.test_week_liquidity_p10, 2)}, under the covenant the point forecast cleared. Flip the chart to Probabilistic to see it.`,
  },
  run_scenario: {
    started: 'Testing what actually moves the covenant: slipping collections, accelerating Vantage, deferring the capex deposit, flexing sales, stretching AP.',
    completed: (o) => {
      if (o?.sweep) {
        const top = o.sweep[0]
        return `Driver sweep complete. Biggest lever: ${top?.label} (${top?.delta_covenant_headroom > 0 ? '+' : ''}${fmtM(top?.delta_covenant_headroom, 2)} of week-13 headroom). Note the levers that do nothing: moves inside the quarter cannot help a quarter-end covenant.`
      }
      const r = o?.result
      return r
        ? `Scenario: Δ headroom ${fmtM(r.delta_covenant_headroom, 2)}, breach probability ${fmtPct(r.p_covenant_breach, 1)}.`
        : 'Scenario complete.'
    },
  },
  compute_variance: {
    started: 'Back-testing: bridging the last 4 weeks of actual collections against what the prior forecast said. A forecast that can explain its own last miss earns trust for the next thirteen weeks.',
    completed: (o) =>
      `Collections ran ${fmtPct(Math.abs(o?.variance_pct_of_forecast || 0), 1)} under forecast; ${fmtPct(o?.attribution?.vantage_share_of_miss, 0)} of the miss is one slipped Vantage invoice. Timing on a collectible receivable, not volume. Same behavior now baked into the week-7 landing.`,
  },
  draft_cash_narrative: {
    started: 'Writing the sponsor commentary: the position, the path and the trough, what the probabilistic view adds, and recommended actions with their quantified effect on covenant headroom.',
    completed: (o) =>
      `Draft ready: ${o?.section_count} sections plus a single recommended action. Nothing goes to Granite Peak until a human signs off.`,
  },
  submit_for_review: {
    started: 'The governance gate. The pipeline is blocked. A human must approve, edit, or reject every section and sign off on the recommended action. The agent proposes; the human disposes.',
    completed: () => 'Review received. The agent logs the trail and finalizes with the reviewer\'s dispositions applied.',
  },
  log_output: {
    started: 'Writing the audit trail: every tool call, every number, the draft, the review decisions, the final output. The answer to "where did this figure come from" six weeks from now.',
    completed: () => 'Audit trail written. The complete decision chain is preserved and reproducible.',
  },
}

function FeedIcon({ type }) {
  const base = 'w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5'
  if (type === 'step_started') {
    return (
      <div className={`${base} bg-amber-100`}>
        <svg className="w-3.5 h-3.5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
        </svg>
      </div>
    )
  }
  if (type === 'step_completed') {
    return (
      <div className={`${base} bg-green-100`}>
        <svg className="w-3.5 h-3.5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </div>
    )
  }
  if (type === 'agent_text') {
    return (
      <div className={`${base} bg-slate-100`}>
        <svg className="w-3.5 h-3.5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      </div>
    )
  }
  if (type === 'review_requested') {
    return (
      <div className={`${base} bg-amber-100`}>
        <svg className="w-3.5 h-3.5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
    )
  }
  if (type === 'pipeline_complete' || type === 'report_generated') {
    return (
      <div className={`${base} bg-green-100`}>
        <svg className="w-3.5 h-3.5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
    )
  }
  return (
    <div className={`${base} bg-slate-100`}>
      <div className="w-2 h-2 rounded-full bg-slate-400" />
    </div>
  )
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function getNarration(item) {
  const { type, step, output, text } = item

  if (type === 'agent_text' && text) {
    return text.length > 400 ? text.slice(0, 397) + '...' : text
  }
  if (type === 'step_started' && STEP_NARRATION[step]) {
    return STEP_NARRATION[step].started
  }
  if (type === 'step_completed' && STEP_NARRATION[step]) {
    return STEP_NARRATION[step].completed(output)
  }
  if (type === 'review_requested') {
    return `The agent has submitted ${item.sectionCount || '?'} narrative sections and its recommended treasury action for review. The workflow is paused. Nothing moves until a human disposes of every item. This is the governance gate.`
  }
  if (type === 'report_generated') {
    return 'The 13-week cash flow workbook has been generated from the same engine the agent used — receipts by customer, disbursements by category, the revolver block, and the covenant test. Download it below.'
  }
  if (type === 'pipeline_complete') {
    return 'Forecast complete. The agent built the deterministic path, quantified the breach risk the point estimate hides, ranked the levers, drafted the narrative, obtained human sign-off, and logged the full audit trail. Click any step on the left to inspect its work.'
  }
  return null
}

const STEP_DISPLAY = {
  load_facility_and_position: 'Position & Facility',
  load_receivables: 'Receivables',
  load_payables_and_fixed: 'Payables & Fixed',
  build_deterministic_forecast: 'Deterministic Forecast',
  run_monte_carlo: 'Monte Carlo',
  run_scenario: 'Scenarios',
  compute_variance: 'Trailing Variance',
  draft_cash_narrative: 'Treasury Narrative',
  submit_for_review: 'Governance Gate',
  log_output: 'Audit Trail',
}

const TYPE_LABELS = {
  step_started: 'Starting',
  step_completed: 'Complete',
  agent_text: 'Agent',
  review_requested: 'Action Required',
  report_generated: 'Workbook Ready',
  pipeline_complete: 'Forecast Complete',
}

export default function ActivityFeed({ feedEvents, pipelineStatus, onViewAuditTrail, onDownloadReport, reportReady }) {
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [feedEvents.length])

  if (!feedEvents.length) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-400 text-base">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p>Agent is starting up...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col">
      <h2 className="text-xl font-bold text-slate-800 mb-1 flex items-center gap-2">
        <svg className="w-5 h-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        What the Agent Is Doing
      </h2>
      <p className="text-sm text-slate-400 mb-4">Follow along as the agent works through the forecast.</p>

      <div ref={scrollRef} className="max-h-[420px] overflow-y-auto space-y-2 pr-1">
        {feedEvents.map((item, i) => {
          const narration = getNarration(item)
          if (!narration) return null

          const label = item.step ? STEP_DISPLAY[item.step] || item.step : TYPE_LABELS[item.type]
          const isLatest = i === feedEvents.length - 1
          const isComplete = item.type === 'pipeline_complete'

          return (
            <div
              key={item.id || i}
              className={`flex gap-3 p-3 rounded-lg transition-colors ${
                isComplete ? 'bg-green-50 border border-green-200' :
                isLatest ? 'bg-amber-50/60 border border-amber-200/60' :
                'bg-white border border-slate-100'
              }`}
            >
              <FeedIcon type={item.type} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-sm font-semibold ${isComplete ? 'text-green-800' : 'text-slate-700'}`}>{label}</span>
                  <span className="text-xs text-slate-400 font-mono">{formatTime(item.timestamp)}</span>
                </div>
                <p className={`text-sm leading-relaxed ${
                  item.type === 'agent_text' ? 'text-slate-500 italic' :
                  isComplete ? 'text-green-700' : 'text-slate-600'
                }`}>
                  {narration}
                </p>
              </div>
            </div>
          )
        })}

        {feedEvents[feedEvents.length - 1]?.type === 'step_started' && (
          <div className="flex items-center gap-2 px-3 py-2 text-amber-600 text-sm">
            <div className="w-4 h-4 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
            <span>Working...</span>
          </div>
        )}

        {pipelineStatus === 'complete' && (
          <div className="mt-4 pt-4 border-t border-slate-200 space-y-3">
            {onDownloadReport && reportReady && (
              <div>
                <button
                  onClick={onDownloadReport}
                  className="w-full flex items-center justify-center gap-2 px-5 py-3 bg-[#3B5998] text-white
                             font-semibold rounded-lg text-base hover:bg-[#2d4373] transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download 13-Week Workbook (Excel)
                </button>
                <p className="text-xs text-slate-400 text-center mt-2">
                  The traditional TWCF, reviewed and approved — receipts by customer, disbursements by category, the covenant block.
                </p>
              </div>
            )}
            {onViewAuditTrail && (
              <button
                onClick={onViewAuditTrail}
                className="w-full flex items-center justify-center gap-2 px-5 py-2.5 bg-white text-[#3B5998]
                           font-semibold rounded-lg text-base border border-[#3B5998] hover:bg-blue-50 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                View Complete Audit Trail
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
