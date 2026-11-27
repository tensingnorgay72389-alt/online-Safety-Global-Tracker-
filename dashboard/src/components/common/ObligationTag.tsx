import type { ObligationType } from '../../types'
import { OBLIGATION_TYPE_META } from '../../types'

interface ObligationTagProps {
  type: string
  thresholdAge?: number | null
  thresholdLabel?: string | null
}

function humanise(type: string) {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function ObligationTag({ type, thresholdAge, thresholdLabel }: ObligationTagProps) {
  const meta = OBLIGATION_TYPE_META[type as ObligationType]
  if (!meta) {
    return (
      <span className="inline-flex items-center rounded-md bg-slate-100 text-slate-600 text-xs font-medium px-2 py-0.5">
        {humanise(type)}
      </span>
    )
  }
  void thresholdAge

  const resolvedThresholdLabel =
    thresholdLabel?.trim() || null

  return (
    <span
      className="inline-flex items-center gap-1 rounded-md text-xs font-medium px-2 py-0.5"
      style={{
        backgroundColor: `${meta.color}12`,
        color: meta.color,
      }}
    >
      {meta.label}
      {resolvedThresholdLabel && (
        <span className="opacity-70">({resolvedThresholdLabel})</span>
      )}
    </span>
  )
}
