import { useCallback, useEffect, useRef, useState } from 'react'

const STEP_NAMES = [
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

const STEP_LABELS = {
  load_facility_and_position: 'Position & Facility',
  load_receivables: 'Receivables',
  load_payables_and_fixed: 'Payables & Fixed Items',
  build_deterministic_forecast: 'Deterministic Forecast',
  run_monte_carlo: 'Monte Carlo',
  run_scenario: 'Sensitivity & Scenarios',
  compute_variance: 'Trailing Variance',
  draft_cash_narrative: 'Treasury Narrative',
  submit_for_review: 'Human Review',
  log_output: 'Audit Log',
}

const initialStepStates = () =>
  Object.fromEntries(STEP_NAMES.map((name) => [name, 'waiting']))

export default function useAgentSocket() {
  const [pipelineStatus, setPipelineStatus] = useState('idle')
  const [stepStates, setStepStates] = useState(initialStepStates)
  const [stepOutputs, setStepOutputs] = useState({})
  const [reviewSections, setReviewSections] = useState([])
  const [reviewAction, setReviewAction] = useState(null)
  const [reviewMessage, setReviewMessage] = useState('')
  const [auditEvents, setAuditEvents] = useState([])
  const [feedEvents, setFeedEvents] = useState([])
  const [replayMode, setReplayMode] = useState(false)
  const [reportReady, setReportReady] = useState(false)
  const [backendAvailable, setBackendAvailable] = useState(false)
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)
  const feedIdRef = useRef(0)

  const clearAll = useCallback(() => {
    setStepStates(initialStepStates())
    setStepOutputs({})
    setReviewSections([])
    setReviewAction(null)
    setReviewMessage('')
    setAuditEvents([])
    setFeedEvents([])
    setReportReady(false)
    feedIdRef.current = 0
  }, [])

  const handleEvent = useCallback((msg) => {
    const { event, data, timestamp } = msg

    setAuditEvents((prev) => [...prev, { event, data, timestamp }])

    switch (event) {
      case 'pipeline_started':
        setPipelineStatus('running')
        clearAll()
        break

      case 'step_started':
        setPipelineStatus((prev) => (prev === 'idle' ? 'running' : prev))
        setStepStates((prev) => ({ ...prev, [data.step]: 'running' }))
        setFeedEvents((prev) => [...prev, {
          id: ++feedIdRef.current,
          type: 'step_started',
          step: data.step,
          input: data.input,
          timestamp,
        }])
        if (data.step === 'submit_for_review') {
          setPipelineStatus('review')
        }
        break

      case 'step_completed':
        setStepStates((prev) => ({ ...prev, [data.step]: 'complete' }))
        setStepOutputs((prev) => {
          // The scenario tool fires once per what-if; accumulate them.
          if (data.step === 'run_scenario') {
            const existing = prev.run_scenario || []
            return { ...prev, run_scenario: [...existing, data.output] }
          }
          return { ...prev, [data.step]: data.output }
        })
        setFeedEvents((prev) => [...prev, {
          id: ++feedIdRef.current,
          type: 'step_completed',
          step: data.step,
          output: data.output,
          timestamp,
        }])
        break

      case 'agent_text':
        setFeedEvents((prev) => [...prev, {
          id: ++feedIdRef.current,
          type: 'agent_text',
          text: data.text,
          timestamp,
        }])
        break

      case 'review_requested':
        setPipelineStatus('review')
        setReviewSections(data.sections || [])
        setReviewAction(data.recommended_action || null)
        setReviewMessage(data.message || '')
        setStepStates((prev) => ({ ...prev, submit_for_review: 'needs-review' }))
        setFeedEvents((prev) => [...prev, {
          id: ++feedIdRef.current,
          type: 'review_requested',
          sectionCount: data.sections?.length || 0,
          timestamp,
        }])
        break

      case 'report_generated':
        setReportReady(true)
        setFeedEvents((prev) => [...prev, {
          id: ++feedIdRef.current,
          type: 'report_generated',
          path: data.path,
          timestamp,
        }])
        break

      case 'pipeline_complete':
        setPipelineStatus('complete')
        setFeedEvents((prev) => [...prev, {
          id: ++feedIdRef.current,
          type: 'pipeline_complete',
          timestamp,
        }])
        break

      case 'pipeline_error':
        setPipelineStatus('error')
        break

      case 'pipeline_reset':
        setPipelineStatus('idle')
        clearAll()
        break
    }
  }, [clearAll])

  // Check if backend is available (retries for up to 10 seconds on startup)
  useEffect(() => {
    let cancelled = false
    let attempts = 0
    async function check() {
      try {
        const res = await fetch('/api/status')
        if (!cancelled && res.ok) setBackendAvailable(true)
      } catch {
        if (!cancelled && attempts < 10) {
          attempts++
          setTimeout(check, 1000)
        }
      }
    }
    check()
    return () => { cancelled = true }
  }, [])

  const syncState = useCallback(async () => {
    try {
      const res = await fetch('/api/events')
      const { events } = await res.json()
      if (events?.length) {
        setPipelineStatus('idle')
        clearAll()
        for (const evt of events) {
          handleEvent(evt)
        }
      }
    } catch {
      // server not ready yet
    }
  }, [handleEvent, clearAll])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`)

    ws.onopen = () => {
      syncState()
    }

    ws.onmessage = (event) => {
      handleEvent(JSON.parse(event.data))
    }

    ws.onclose = () => {
      reconnectTimer.current = setTimeout(connect, 2000)
    }

    ws.onerror = () => {
      ws.close()
    }

    wsRef.current = ws
  }, [syncState, handleEvent])

  useEffect(() => {
    if (!backendAvailable) return
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [backendAvailable, connect])

  const sendReview = useCallback((decisions, recommendedActionDisposition) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        event: 'review_submitted',
        data: {
          decisions,
          recommended_action_disposition: recommendedActionDisposition,
        },
      }))
      setStepStates((prev) => ({ ...prev, submit_for_review: 'complete' }))
      setPipelineStatus('running')
    }
  }, [])

  const startPipeline = useCallback(async () => {
    setPipelineStatus('running')
    clearAll()
    await fetch('/api/run', { method: 'POST' })
  }, [clearAll])

  const resetPipeline = useCallback(async () => {
    await fetch('/api/reset', { method: 'POST' })
  }, [])

  const downloadReport = useCallback(async () => {
    // Live backend serves the freshly generated workbook; the deployed replay
    // demo (no backend) falls back to the static asset committed in /public.
    const url = backendAvailable ? '/api/report' : '/cashflow_13wk.xlsx'
    try {
      const res = await fetch(url)
      if (!res.ok) return
      const blob = await res.blob()
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = 'cascade-precision-13-week-cashflow.xlsx'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(objectUrl)
    } catch {
      // workbook not available
    }
  }, [backendAvailable])

  const startReplay = useCallback(async () => {
    setReplayMode(true)
    setPipelineStatus('running')
    clearAll()

    let events = null
    try {
      const res = await fetch('/api/replay')
      const data = await res.json()
      events = data.events
    } catch {
      // no backend, try static file
    }

    if (!events?.length) {
      try {
        const res = await fetch('/replay_capture.json')
        const data = await res.json()
        events = data.events
      } catch {
        // no replay data available
      }
    }

    if (!events?.length) {
      setPipelineStatus('idle')
      setReplayMode(false)
      return
    }

    for (let i = 0; i < events.length; i++) {
      const evt = events[i]
      if (i > 0) {
        const prev = new Date(events[i - 1].timestamp).getTime()
        const curr = new Date(evt.timestamp).getTime()
        // Replay at 0.3x real speed, capped at 4s per gap
        const gap = Math.min((curr - prev) * 0.3, 4000)
        if (gap > 50) await new Promise((r) => setTimeout(r, gap))
      }
      handleEvent(evt)
    }

    setReplayMode(false)
  }, [handleEvent, clearAll])

  return {
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
    STEP_NAMES,
    STEP_LABELS,
  }
}
