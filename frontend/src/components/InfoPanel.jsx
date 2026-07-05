export default function InfoPanel({ open, onClose }) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      <div className="absolute inset-0 bg-slate-900/30" />
      <div
        className="relative w-[520px] max-w-full h-full bg-white shadow-2xl overflow-y-auto p-8"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-5 right-5 w-8 h-8 flex items-center justify-center rounded-lg
                     text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          aria-label="Close"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>

        <h2 className="text-2xl font-bold text-slate-800 mb-1">About this demo</h2>
        <p className="text-sm text-slate-500 mb-6">
          An agent harness for treasury forecasting — deterministic control, probabilistic reasoning.
        </p>

        <div className="space-y-5 text-[15px] text-slate-700 leading-relaxed">
          <p>
            Cascade Precision Products ($72M contract manufacturer, ~240 employees) was acquired
            ten weeks ago by Granite Peak Partners in a leveraged buyout. The sponsor's first
            standing ask: a weekly 13-week cash flow with covenant visibility. This is week one.
          </p>

          <div>
            <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-2">The three layers</h3>
            <div className="space-y-3">
              <div className="border border-slate-200 rounded-lg p-4">
                <p className="font-semibold text-slate-800 mb-1">Governance</p>
                <p className="text-sm text-slate-600">
                  A $1.5M operating cash floor, a $4.0M liquidity covenant tested at week 13, a
                  human review gate that truly blocks the pipeline, and a complete audit trail.
                  These are features to show, not plumbing to hide.
                </p>
              </div>
              <div className="border border-slate-200 rounded-lg p-4">
                <p className="font-semibold text-slate-800 mb-1">Finance</p>
                <p className="text-sm text-slate-600">
                  Where is the trough, what threatens the covenant, and what should management do.
                  Every number cites its driver; timing is distinguished from structural.
                </p>
              </div>
              <div className="border border-slate-200 rounded-lg p-4">
                <p className="font-semibold text-slate-800 mb-1">Capability</p>
                <p className="text-sm text-slate-600">
                  A deterministic roll-forward engine with revolver mechanics, plus a Monte Carlo
                  layer that re-runs it a thousand times over measured payment behavior. The
                  single-point forecast passes the covenant; the distribution says there is a
                  ~20% chance it doesn't.
                </p>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-2">Why it can't drift</h3>
            <p className="text-sm text-slate-600">
              This UI wraps the exact same Python functions the analysis notebook runs. The engine
              is pure; the frontend only renders what the tools return. If a number differed
              between the notebook and this screen, the wrapper would be wrong, not the engine.
            </p>
          </div>

          <div>
            <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-2">The point</h3>
            <p className="text-sm text-slate-600">
              Judgment, not automation for its own sake. The agent proposes; the human disposes
              at the gate. The deliverable is the same 13-week workbook a treasury team would
              build by hand — plus the breach probability no spreadsheet was going to volunteer.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
