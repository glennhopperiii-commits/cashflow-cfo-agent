import { useState } from 'react'

const CONFIDENCE_COLORS = {
  high: 'bg-green-100 text-green-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-red-100 text-red-700',
}

export default function ReviewSection({ section, onDecision }) {
  const [action, setAction] = useState(null)
  const [editedContent, setEditedContent] = useState(section.content)
  const [notes, setNotes] = useState('')
  const [editing, setEditing] = useState(false)

  const handleApprove = () => {
    setAction('approved')
    setEditing(false)
    onDecision({
      section_title: section.title,
      action: 'approved',
      edited_content: null,
      notes: '',
    })
  }

  const handleEdit = () => {
    setEditing(true)
    setAction('edited')
  }

  const handleSaveEdit = () => {
    setEditing(false)
    onDecision({
      section_title: section.title,
      action: 'edited',
      edited_content: editedContent,
      notes: 'Edited at review gate.',
    })
  }

  const handleReject = () => {
    setAction('rejected')
    setEditing(false)
    onDecision({
      section_title: section.title,
      action: 'rejected',
      edited_content: null,
      notes,
    })
  }

  const decided = action && (action !== 'edited' || !editing)

  return (
    <div className={`bg-white border rounded-lg p-5 transition-all ${
      decided
        ? action === 'approved' ? 'border-green-300 bg-green-50/30'
          : action === 'rejected' ? 'border-red-300 bg-red-50/30'
          : 'border-amber-300 bg-amber-50/30'
        : 'border-slate-200'
    }`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-slate-800 text-base">{section.title}</h3>
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${CONFIDENCE_COLORS[section.confidence]}`}>
          {section.confidence} confidence
        </span>
      </div>

      {editing ? (
        <div className="mb-4">
          <textarea
            value={editedContent}
            onChange={(e) => setEditedContent(e.target.value)}
            className="w-full h-40 p-3 text-sm border border-slate-300 rounded-lg font-sans
                       focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={handleSaveEdit}
              className="px-3 py-1.5 bg-amber-500 text-white text-sm font-medium rounded
                         hover:bg-amber-600 transition-colors"
            >
              Save Edit
            </button>
            <button
              onClick={() => { setEditing(false); setAction(null) }}
              className="px-3 py-1.5 text-sm text-slate-600 hover:text-slate-800"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="text-[15px] text-slate-700 leading-relaxed whitespace-pre-wrap mb-4">
          {action === 'edited' ? editedContent : section.content}
        </div>
      )}

      {section.open_flags?.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-amber-700 mb-1">Open flags:</p>
          <ul className="text-xs text-amber-600 space-y-0.5">
            {section.open_flags.map((flag, i) => (
              <li key={i} className="flex items-start gap-1">
                <span className="mt-1 w-1 h-1 bg-amber-500 rounded-full shrink-0" />
                {flag}
              </li>
            ))}
          </ul>
        </div>
      )}

      {action === 'rejected' && !editing && (
        <div className="mb-4">
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Reason for rejection..."
            className="w-full p-2 text-sm border border-red-300 rounded focus:outline-none focus:ring-2 focus:ring-red-400"
            onBlur={() => onDecision({
              section_title: section.title,
              action: 'rejected',
              edited_content: null,
              notes,
            })}
          />
        </div>
      )}

      {!decided && !editing && (
        <div className="flex gap-2">
          <button
            onClick={handleApprove}
            className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg
                       hover:bg-green-700 transition-colors"
          >
            Approve
          </button>
          <button
            onClick={handleEdit}
            className="px-4 py-2 bg-amber-500 text-white text-sm font-medium rounded-lg
                       hover:bg-amber-600 transition-colors"
          >
            Edit
          </button>
          <button
            onClick={handleReject}
            className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg
                       hover:bg-red-700 transition-colors"
          >
            Reject
          </button>
        </div>
      )}

      {decided && !editing && (
        <div className="flex items-center gap-2 text-sm">
          <span className={`font-medium ${
            action === 'approved' ? 'text-green-600' : action === 'rejected' ? 'text-red-600' : 'text-amber-600'
          }`}>
            {action === 'approved' ? 'Approved' : action === 'rejected' ? 'Rejected' : 'Edited'}
          </span>
          <button
            onClick={() => { setAction(null); setEditing(false) }}
            className="text-xs text-slate-400 hover:text-slate-600"
          >
            Change
          </button>
        </div>
      )}
    </div>
  )
}
