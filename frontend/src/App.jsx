import { useCallback, useState } from 'react'
import useAgentSocket from './hooks/useAgentSocket'
import Header from './components/Header'
import PipelineView from './components/PipelineView'
import ReviewGate from './components/ReviewGate'
import ActivityFeed from './components/ActivityFeed'
import ForecastDashboard from './components/ForecastDashboard'
import AuditLog from './components/AuditLog'
import InfoPanel from './components/InfoPanel'
import PasswordGate from './components/PasswordGate'

const ACCESS_PASSWORD = import.meta.env.VITE_ACCESS_PASSWORD || ''

function IdleIntro() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="max-w-md text-center space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 mb-2">13-Week Cash Flow Forecast</h2>
          <p className="text-base text-slate-500">
            The same weekly forecast your treasury team builds by hand — with a deterministic
            engine, a probabilistic layer, and a human gate before anything reaches the sponsor.
          </p>
        </div>

        <div className="text-left bg-white border border-slate-200 rounded-lg p-5 space-y-3">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">What it will do</h3>
          <ul className="space-y-2 text-sm text-slate-600">
            <li className="flex gap-2"><span className="text-[#3B5998] font-bold shrink-0">1.</span>Load the position: cash, revolver, floor, covenant, debt service</li>
            <li className="flex gap-2"><span className="text-[#3B5998] font-bold shrink-0">2.</span>Load AR with observed payment behavior and AP with the fixed schedule</li>
            <li className="flex gap-2"><span className="text-[#3B5998] font-bold shrink-0">3.</span>Roll 13 weeks deterministically with revolver auto-draw and sweep</li>
            <li className="flex gap-2"><span className="text-[#3B5998] font-bold shrink-0">4.</span>Re-run the engine 1,000 times over timing and volume — the P10–P90 fan</li>
            <li className="flex gap-2"><span className="text-[#3B5998] font-bold shrink-0">5.</span>Sweep the drivers: what actually moves week-13 covenant headroom</li>
            <li className="flex gap-2"><span className="text-[#3B5998] font-bold shrink-0">6.</span>Back-test the trailing 4 weeks and draft the sponsor narrative</li>
            <li className="flex gap-2"><span className="text-amber-500 font-bold shrink-0">7.</span><span><strong>Stop and wait</strong> for human review of every section and the recommended action</span></li>
            <li className="flex gap-2"><span className="text-[#3B5998] font-bold shrink-0">8.</span>Log the audit trail and produce the 13-week workbook</li>
          </ul>
        </div>

        <p className="text-sm text-slate-400">
          The agent cannot skip the review gate or send anything to the sponsor without approval.
        </p>
      </div>
    </div>
  )
}

function App() {
  const [infoPanelOpen, setInfoPanelOpen] = useState(false)
  const [auditTrailOpen, setAuditTrailOpen] = useState(false)

  const {
    pipelineStatus,
    stepStates,
    stepOutputs,
    reviewSections,
    reviewAction,
    reviewMessage,
    auditEvents,
    feedEvents,
    replayMode,
    reportReady,
    backendAvailable,
    sendReview,
    startPipeline,
    resetPipeline,
    startReplay,
    downloadReport,
  } = useAgentSocket()

  const showReview = pipelineStatus === 'review' && reviewSections.length > 0
  const isActive = pipelineStatus === 'running' || pipelineStatus === 'complete' || pipelineStatus === 'error'
  const det = stepOutputs.build_deterministic_forecast
  const mc = stepOutputs.run_monte_carlo

  const handleViewAuditTrail = useCallback(() => setAuditTrailOpen(true), [])
  const handleReset = useCallback(async () => {
    setAuditTrailOpen(false)
    await resetPipeline()
  }, [resetPipeline])

  return (
    <PasswordGate password={ACCESS_PASSWORD}>
    <div className="h-screen flex flex-col bg-[var(--color-bg)] overflow-auto">
      <Header
        pipelineStatus={pipelineStatus}
        onRun={startPipeline}
        onReset={handleReset}
        onReplay={startReplay}
        replayMode={replayMode}
        backendAvailable={backendAvailable}
        onInfoOpen={() => setInfoPanelOpen(true)}
      />

      <InfoPanel open={infoPanelOpen} onClose={() => setInfoPanelOpen(false)} />

      <main className="flex-1 flex gap-6 p-6 max-w-[1700px] mx-auto w-full min-h-0">
        <div className="w-[36%] shrink-0 overflow-y-auto">
          <PipelineView
            stepStates={stepStates}
            stepOutputs={stepOutputs}
            pipelineStatus={pipelineStatus}
            reviewSections={reviewSections}
          />
        </div>

        <div className="w-[64%] overflow-y-auto">
          {showReview ? (
            <ReviewGate
              sections={reviewSections}
              recommendedAction={reviewAction}
              message={reviewMessage}
              onSubmitReview={sendReview}
            />
          ) : isActive ? (
            <div className="space-y-6">
              <ForecastDashboard
                det={det}
                mc={mc}
                scenarios={stepOutputs.run_scenario}
                variance={stepOutputs.compute_variance}
              />
              <ActivityFeed
                feedEvents={feedEvents}
                pipelineStatus={pipelineStatus}
                onViewAuditTrail={handleViewAuditTrail}
                onDownloadReport={downloadReport}
                reportReady={reportReady}
              />
            </div>
          ) : (
            <IdleIntro />
          )}
        </div>
      </main>

      <AuditLog events={auditEvents} forceOpen={auditTrailOpen} />
    </div>
    </PasswordGate>
  )
}

export default App
