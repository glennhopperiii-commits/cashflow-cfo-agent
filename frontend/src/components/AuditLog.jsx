import { useEffect, useRef, useState } from 'react'

const EVENT_LABELS = {
  step_started: 'Step Started',
  step_completed: 'Step Completed',
  agent_text: 'Agent Output',
  review_requested: 'Review Requested',
  review_completed: 'Review Completed',
  report_generated: 'Workbook Generated',
  pipeline_complete: 'Pipeline Complete',
  pipeline_error: 'Pipeline Error',
  pipeline_reset: 'Pipeline Reset',
  pipeline_started: 'Pipeline Started',
}

const EVENT_COLORS = {
  step_started: 'bg-amber-400',
  step_completed: 'bg-green-500',
  agent_text: 'bg-slate-400',
  review_requested: 'bg-amber-500',
  review_completed: 'bg-green-500',
  report_generated: 'bg-[#3B5998]',
  pipeline_complete: 'bg-green-600',
  pipeline_error: 'bg-red-500',
  pipeline_reset: 'bg-slate-400',
  pipeline_started: 'bg-slate-500',
}

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export default function AuditLog({ events, forceOpen }) {
  const [open, setOpen] = useState(false)
  const [expandedIndex, setExpandedIndex] = useState(null)
  const panelRef = useRef(null)

  useEffect(() => {
    if (forceOpen && !open) {
      setOpen(true)
      setTimeout(() => {
        panelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 100)
    }
  }, [forceOpen])  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div ref={panelRef} className="border-t border-slate-200 bg-white">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>
            <span className="font-semibold text-base text-slate-800">Audit Trail</span>
            {events.length > 0 && (
              <span className="ml-2 text-sm text-slate-400 font-normal">
                {events.length} events recorded
              </span>
            )}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {!open && events.length > 0 && (
            <span className="text-xs text-[#3B5998] font-medium">Click to inspect</span>
          )}
          <svg className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {open && (
        <div className="px-6 pb-4 max-h-[50vh] overflow-y-auto">
          {events.length === 0 ? (
            <p className="text-sm text-slate-400 py-4">No events yet.</p>
          ) : (
            <div className="space-y-1">
              {events.map((evt, i) => (
                <div key={i} className="flex items-start gap-3 py-1.5">
                  <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${EVENT_COLORS[evt.event] || 'bg-slate-400'}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-slate-400">{formatTime(evt.timestamp)}</span>
                      <span className="text-sm font-medium text-slate-700">
                        {EVENT_LABELS[evt.event] || evt.event}
                      </span>
                      {evt.data?.step && (
                        <span className="text-xs text-slate-500">{evt.data.step}</span>
                      )}
                      <button
                        onClick={() => setExpandedIndex(expandedIndex === i ? null : i)}
                        className="text-xs text-[#3B5998] hover:text-[#2d4373]"
                      >
                        {expandedIndex === i ? 'hide' : 'detail'}
                      </button>
                    </div>
                    {expandedIndex === i && (
                      <pre className="mt-2 p-2 bg-slate-50 rounded text-xs font-mono text-slate-600 overflow-x-auto max-h-40">
                        {JSON.stringify(evt.data, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
