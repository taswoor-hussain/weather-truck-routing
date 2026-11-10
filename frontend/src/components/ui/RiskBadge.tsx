import { RISK_META } from '../../lib/risk'
import type { RiskLevel } from '../../types/api'

export function RiskBadge({ level, className = '' }: { level: RiskLevel; className?: string }) {
  const meta = RISK_META[level]
  return (
    <span
      className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-xs font-semibold whitespace-nowrap ring-1 ring-inset ${meta.badgeClass} ${className}`}
    >
      {meta.label}
    </span>
  )
}
