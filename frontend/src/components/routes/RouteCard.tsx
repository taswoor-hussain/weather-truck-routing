import { formatDuration, formatFullDateTime, formatMiles } from '../../lib/format'
import { RISK_META } from '../../lib/risk'
import type { RiskLevel, RouteOption } from '../../types/api'
import { CheckpointTable } from './CheckpointTable'
import { RiskBreakdownBar } from './RiskBreakdownBar'

const HIGHLIGHTED_LEVELS: RiskLevel[] = ['no_travel', 'severe', 'high']

interface RouteCardProps {
  route: RouteOption
  color: string
  selected: boolean
  onSelect: (routeId: number) => void
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[11px] tracking-wide text-slate-500 uppercase">{label}</dt>
      <dd className="text-sm font-semibold text-slate-900 tabular-nums">{value}</dd>
    </div>
  )
}

export function RouteCard({ route, color, selected, onSelect }: RouteCardProps) {
  const hazards = HIGHLIGHTED_LEVELS.filter((level) => route.risk_miles[level] >= 0.5)

  return (
    <article
      className={`rounded-xl bg-white p-3.5 ring-1 transition-shadow ${
        selected ? 'shadow-md ring-2 ring-blue-600' : 'ring-slate-200 hover:shadow-sm'
      }`}
    >
      <button
        type="button"
        onClick={() => onSelect(route.id)}
        aria-pressed={selected}
        className="block w-full text-left focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-700"
      >
        <header className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="flex items-center gap-2 font-semibold text-slate-900">
              <span className="size-3 shrink-0 rounded-full" style={{ backgroundColor: color }} aria-hidden="true" />
              Route {route.label}
            </h3>
            <p className="mt-0.5 truncate text-xs text-slate-500" title={route.summary}>
              {route.summary ? `via ${route.summary}` : 'Local roads'}
            </p>
          </div>
          {route.is_recommended && (
            <span className="shrink-0 rounded-full bg-emerald-600 px-2 py-0.5 text-[11px] font-semibold text-white">
              Recommended
            </span>
          )}
        </header>

        <dl className="mt-3 grid grid-cols-3 gap-2">
          <Stat label="Distance" value={formatMiles(route.distance_mi)} />
          <Stat label="Drive time" value={formatDuration(route.duration_s)} />
          <Stat label="Avg risk" value={route.average_risk.toFixed(2)} />
        </dl>
        <p className="mt-1.5 text-xs text-slate-500">Arrives {formatFullDateTime(route.arrival_time)}</p>

        <div className="mt-3">
          <RiskBreakdownBar riskMiles={route.risk_miles} />
          <p className="mt-1.5 text-xs text-slate-600">
            {hazards.length === 0
              ? 'No High, Severe or No Travel miles'
              : hazards.map((level) => (
                  <span key={level} className="mr-3 inline-flex items-center gap-1">
                    <span className="size-2 rounded-full" style={{ backgroundColor: RISK_META[level].color }} />
                    {formatMiles(route.risk_miles[level])} {RISK_META[level].label.toLowerCase()}
                  </span>
                ))}
          </p>
        </div>
      </button>

      {selected && (
        <div className="mt-3">
          <h4 className="mb-1.5 text-xs font-semibold text-slate-600">
            {route.checkpoints.length} weather checkpoints
          </h4>
          <CheckpointTable checkpoints={route.checkpoints} />
        </div>
      )}
    </article>
  )
}
