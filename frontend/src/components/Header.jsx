const PIPELINE_STATUS_LABELS = {
  idle: 'Ready',
  running: 'Running',
  review: 'Awaiting Review',
  complete: 'Complete',
  error: 'Error',
}

const PIPELINE_STATUS_COLORS = {
  idle: 'text-slate-500',
  running: 'text-amber-600',
  review: 'text-amber-600',
  complete: 'text-green-600',
  error: 'text-red-600',
}

export default function Header({ pipelineStatus, onRun, onReset, onReplay, replayMode, backendAvailable, onInfoOpen }) {
  const isRunning = pipelineStatus === 'running' || pipelineStatus === 'review'

  return (
    <header className="bg-white border-b-2 border-slate-200 px-8 py-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[28px] font-bold text-slate-800 tracking-tight">
            Cascade Precision Products
            <span className="text-slate-400 font-normal mx-2">//</span>
            <span className="text-[#3B5998]">13-Week Cash Flow</span>
          </h1>
          <p className="text-lg text-slate-500 mt-0.5">
            Prepared for Granite Peak Partners · week 1 begins Monday, Aug 24, 2026
          </p>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={onInfoOpen}
            className="w-9 h-9 flex items-center justify-center rounded-lg border border-slate-200
                       text-slate-400 hover:text-[#3B5998] hover:border-blue-300 hover:bg-blue-50
                       transition-colors"
            aria-label="About this demo"
            title="About this demo"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
          </button>

          <div className="w-px h-6 bg-slate-200" />

          <span className={`text-base font-semibold ${PIPELINE_STATUS_COLORS[pipelineStatus]}`}>
            {PIPELINE_STATUS_LABELS[pipelineStatus]}
          </span>

          {backendAvailable && (
            <button
              onClick={onRun}
              disabled={isRunning}
              className="px-5 py-2.5 bg-[#3B5998] text-white font-semibold rounded-lg text-base
                         hover:bg-[#2d4373] disabled:opacity-50 disabled:cursor-not-allowed
                         transition-colors"
            >
              Run Forecast
            </button>
          )}

          <button
            onClick={onReset}
            disabled={pipelineStatus === 'idle' && !replayMode}
            className="px-4 py-2.5 bg-slate-200 text-slate-700 font-medium rounded-lg text-base
                       hover:bg-slate-300 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors"
          >
            Reset
          </button>

          <button
            onClick={onReplay}
            disabled={isRunning || replayMode}
            className={`px-5 py-2.5 font-semibold rounded-lg text-base transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed
                       ${backendAvailable
                         ? 'border border-slate-300 text-slate-600 hover:bg-slate-50'
                         : 'bg-[#3B5998] text-white hover:bg-[#2d4373]'
                       }`}
          >
            {replayMode ? 'Replaying...' : backendAvailable ? 'Replay' : 'Play Demo'}
          </button>
        </div>
      </div>
    </header>
  )
}
