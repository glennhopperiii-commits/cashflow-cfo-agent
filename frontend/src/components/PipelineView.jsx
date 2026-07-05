import StepCard from './StepCard'

const PIPELINE_STEPS = [
  'load_facility_and_position',
  'load_receivables',
  'load_payables_and_fixed',
  'build_deterministic_forecast',
  'run_monte_carlo',
  'run_scenario',
  'compute_variance',
  'draft_cash_narrative',
  'submit_for_review',
  'log_output',
]

export default function PipelineView({ stepStates, stepOutputs, pipelineStatus, reviewSections }) {
  return (
    <div className="space-y-3">
      <h2 className="text-xl font-bold text-slate-800 mb-4">Forecast Pipeline</h2>
      <div className="relative">
        <div className="absolute left-[1.85rem] top-0 bottom-0 w-0.5 bg-slate-200 -z-10" />
        <div className="space-y-3">
          {PIPELINE_STEPS.map((stepName) => (
            <StepCard
              key={stepName}
              stepName={stepName}
              status={stepStates[stepName] || 'waiting'}
              output={stepOutputs[stepName]}
              pipelineStatus={pipelineStatus}
              reviewSections={stepName === 'submit_for_review' ? reviewSections : undefined}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
