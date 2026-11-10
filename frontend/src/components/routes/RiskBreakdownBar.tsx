import { RISK_LEVELS, RISK_META } from '../../lib/risk'
import type { RiskLevel } from '../../types/api'

/** Share of route miles at each risk level, as one stacked bar. */
export function RiskBreakdownBar({ riskMiles }: { riskMiles: Record<RiskLevel, number> }) {
  const total = RISK_LEVELS.reduce((sum, level) => sum + riskMiles[level], 0)
  const label = RISK_LEVELS.filter((level) => riskMiles[level] > 0)
    .map((level) => `${RISK_META[level].label} ${Math.round(riskMiles[level])} mi`)
    .join(', ')

  return (
    <div role="img" aria-label={`Risk by distance: ${label}`} className="flex h-2 overflow-hidden rounded-full bg-slate-200">
      {total > 0 &&
        RISK_LEVELS.map((level) =>
          riskMiles[level] > 0 ? (
            <div
              key={level}
              style={{ width: `${(riskMiles[level] / total) * 100}%`, backgroundColor: RISK_META[level].color }}
            />
          ) : null,
        )}
    </div>
  )
}
