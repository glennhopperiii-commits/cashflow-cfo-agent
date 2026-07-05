// Accounting number formats: parentheses for negatives, thousand separators,
// tabular numerals (pair with font-mono in the markup).

export function fmtUSD(value) {
  if (value == null) return ''
  const abs = Math.abs(value)
  const formatted = abs.toLocaleString('en-US', { maximumFractionDigits: 0 })
  return value < 0 ? `($${formatted})` : `$${formatted}`
}

export function fmtK(value) {
  if (value == null) return ''
  const abs = Math.abs(value)
  const k = (abs / 1000).toLocaleString('en-US', { maximumFractionDigits: 0 })
  return value < 0 ? `(${k}K)` : `${k}K`
}

export function fmtM(value, digits = 1) {
  if (value == null) return ''
  const abs = Math.abs(value)
  const m = (abs / 1_000_000).toFixed(digits)
  return value < 0 ? `($${m}M)` : `$${m}M`
}

export function fmtPct(value, digits = 1) {
  if (value == null) return ''
  return `${(value * 100).toFixed(digits)}%`
}

export function fmtDelta(value) {
  if (value == null) return ''
  const abs = Math.abs(value)
  const formatted = abs.toLocaleString('en-US', { maximumFractionDigits: 0 })
  return value < 0 ? `-$${formatted}` : `+$${formatted}`
}
