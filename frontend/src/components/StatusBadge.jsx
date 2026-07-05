const STATUS_CONFIG = {
  waiting: { label: 'Waiting', bg: 'bg-slate-100', text: 'text-slate-500', dot: 'bg-slate-400' },
  running: { label: 'Running', bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500 animate-pulse' },
  complete: { label: 'Complete', bg: 'bg-green-50', text: 'text-green-700', dot: 'bg-green-500' },
  'needs-review': { label: 'Needs Review', bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500' },
  error: { label: 'Error', bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500' },
}

export default function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.waiting

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-sm font-medium ${config.bg} ${config.text}`}>
      <span className={`w-2 h-2 rounded-full ${config.dot}`} />
      {config.label}
    </span>
  )
}
