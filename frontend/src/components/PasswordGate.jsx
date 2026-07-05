import { useState } from 'react'

const COOKIE_NAME = 'cashflow_cfo_auth'
const COOKIE_DAYS = 7

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

function setCookie(name, value, days) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString()
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Strict`
}

export default function PasswordGate({ password, children }) {
  const [authenticated, setAuthenticated] = useState(() => getCookie(COOKIE_NAME) === 'granted')
  const [input, setInput] = useState('')
  const [error, setError] = useState(false)

  if (!password || authenticated) return children

  const handleSubmit = (e) => {
    e.preventDefault()
    if (input === password) {
      setCookie(COOKIE_NAME, 'granted', COOKIE_DAYS)
      setAuthenticated(true)
      setError(false)
    } else {
      setError(true)
      setInput('')
    }
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg)] flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-10 w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-slate-800 mb-1">
            Cascade Precision Products
          </h1>
          <p className="text-[#3B5998] font-semibold text-lg">13-Week Cash Flow Demo</p>
          <p className="text-sm text-slate-500 mt-3">
            AFP FP&amp;A Virtual Summit 2026
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1">
              Access Code
            </label>
            <input
              id="password"
              type="password"
              value={input}
              onChange={(e) => { setInput(e.target.value); setError(false) }}
              placeholder="Enter access code"
              autoFocus
              className={`w-full px-4 py-3 text-base border rounded-lg focus:outline-none focus:ring-2
                ${error
                  ? 'border-red-400 focus:ring-red-400'
                  : 'border-slate-300 focus:ring-blue-500'
                }`}
            />
            {error && (
              <p className="text-sm text-red-600 mt-1">Invalid access code. Please try again.</p>
            )}
          </div>

          <button
            type="submit"
            className="w-full py-3 bg-[#3B5998] text-white font-semibold rounded-lg text-base
                       hover:bg-[#2d4373] transition-colors"
          >
            Enter
          </button>
        </form>

        <p className="text-xs text-slate-400 text-center mt-6">
          Deterministic control, probabilistic reasoning
        </p>
      </div>
    </div>
  )
}
