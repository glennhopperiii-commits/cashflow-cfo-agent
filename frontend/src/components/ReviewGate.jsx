import { useCallback, useState } from 'react'
import ReviewSection from './ReviewSection'
import { fmtUSD, fmtPct } from '../lib/format'

// The recommended-action card: the single treasury action the reviewer signs
// off on before it is "sent to the sponsor." Deliberately prominent.
function RecommendedActionCard({ action, onDecision }) {
  const [disposition, setDisposition] = useState(null)
  const [notes, setNotes] = useState('')

  const decide = (d) => {
    setDisposition(d)
    onDecision({
      action: action.action,
      disposition: d,
      notes,
    })
  }

  return (
    <div className={`border-2 rounded-lg p-5 transition-all ${
      disposition === 'approved' ? 'border-green-400 bg-green-50/40'
        : disposition === 'rejected' ? 'border-red-400 bg-red-50/40'
        : 'border-[#3B5998] bg-blue-50/40'
    }`}>
      <div className="flex items-center gap-2 mb-2">
        <svg className="w-5 h-5 text-[#3B5998]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        <h3 className="font-bold text-slate-800 text-base uppercase tracking-wide">Recommended Treasury Action</h3>
      </div>

      <p className="text-[15px] text-slate-800 font-medium leading-relaxed mb-2">{action.action}</p>
      {action.rationale && (
        <p className="text-sm text-slate-600 leading-relaxed mb-3">{action.rationale}</p>
      )}

      <div className="flex gap-4 mb-4">
        {action.expected_headroom_effect != null && (
          <div className="bg-white border border-slate-200 rounded px-3 py-1.5">
            <span className="text-xs text-slate-400 block">Headroom effect</span>
            <span className="text-sm font-mono font-bold text-green-700">+{fmtUSD(action.expected_headroom_effect)}</span>
          </div>
        )}
        {action.expected_breach_prob_effect != null && (
          <div className="bg-white border border-slate-200 rounded px-3 py-1.5">
            <span className="text-xs text-slate-400 block">Breach probability effect</span>
            <span className="text-sm font-mono font-bold text-green-700">{fmtPct(action.expected_breach_prob_effect, 1)}</span>
          </div>
        )}
      </div>

      {!disposition ? (
        <div className="flex gap-2 items-center">
          <button
            onClick={() => decide('approved')}
            className="px-5 py-2.5 bg-green-600 text-white text-sm font-bold rounded-lg
                       hover:bg-green-700 transition-colors"
          >
            Sign Off — Send to Sponsor
          </button>
          <button
            onClick={() => decide('rejected')}
            className="px-4 py-2.5 bg-red-600 text-white text-sm font-medium rounded-lg
                       hover:bg-red-700 transition-colors"
          >
            Reject
          </button>
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Notes (optional)..."
            className="flex-1 p-2 text-sm border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
      ) : (
        <div className="flex items-center gap-2 text-sm">
          <span className={`font-bold ${disposition === 'approved' ? 'text-green-700' : 'text-red-700'}`}>
            {disposition === 'approved' ? 'Signed off' : 'Rejected'}
          </span>
          <button
            onClick={() => setDisposition(null)}
            className="text-xs text-slate-400 hover:text-slate-600"
          >
            Change
          </button>
        </div>
      )}
    </div>
  )
}

export default function ReviewGate({ sections, recommendedAction, message, onSubmitReview }) {
  const [decisions, setDecisions] = useState({})
  const [actionDisposition, setActionDisposition] = useState(null)
  const [submitted, setSubmitted] = useState(false)

  const handleDecision = useCallback((decision) => {
    setDecisions((prev) => ({ ...prev, [decision.section_title]: decision }))
  }, [])

  const allDecided =
    sections.length > 0 &&
    sections.every((s) => decisions[s.title]) &&
    (!recommendedAction || actionDisposition)

  const handleSubmit = () => {
    onSubmitReview(
      sections.map((s) => decisions[s.title]),
      actionDisposition || { action: '', disposition: 'approved', notes: '' },
    )
    setSubmitted(true)
  }

  if (submitted) {
    const counts = Object.values(decisions).reduce(
      (acc, d) => ({ ...acc, [d.action]: (acc[d.action] || 0) + 1 }), {})
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-slate-800">Review Complete</h2>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-sm text-green-800 font-medium">
            {counts.approved || 0} approved, {counts.edited || 0} edited, {counts.rejected || 0} rejected ·
            recommended action {actionDisposition?.disposition || 'approved'}
          </p>
          <p className="text-sm text-green-600 mt-1">Pipeline is resuming — writing the audit trail...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-800">Review Workspace</h2>
        <p className="text-sm text-slate-500">
          The pipeline is paused. Nothing goes to Granite Peak until every section and the
          recommended action have your disposition.
        </p>
      </div>

      {message && (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm text-slate-700 whitespace-pre-wrap">
          {message}
        </div>
      )}

      {recommendedAction && (
        <RecommendedActionCard action={recommendedAction} onDecision={setActionDisposition} />
      )}

      <div className="space-y-4">
        {sections.map((section) => (
          <ReviewSection
            key={section.title}
            section={section}
            onDecision={handleDecision}
          />
        ))}
      </div>

      <button
        onClick={handleSubmit}
        disabled={!allDecided}
        className="w-full py-3 bg-[#3B5998] text-white font-semibold rounded-lg text-base
                   hover:bg-[#2d4373] disabled:opacity-50 disabled:cursor-not-allowed
                   transition-colors"
      >
        {allDecided
          ? 'Submit Review & Resume Pipeline'
          : `Review all items (${Object.keys(decisions).length + (actionDisposition ? 1 : 0)}/${sections.length + (recommendedAction ? 1 : 0)})`}
      </button>
    </div>
  )
}
