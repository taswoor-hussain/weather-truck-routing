import { memo } from 'react'
import { CircleMarker, Popup } from 'react-leaflet'

import { formatFullDateTime } from '../../lib/format'
import { RISK_META } from '../../lib/risk'
import type { Checkpoint, RiskLevel, RouteOption } from '../../types/api'
import { RiskBadge } from '../ui/RiskBadge'

interface CheckpointMarkersProps {
  routes: RouteOption[]
  selectedRouteId: number | null
}

/**
 * Risk-coloured checkpoint dots. The selected route shows every checkpoint; other
 * routes show only their hazardous ones, so their lines stay readable.
 */
export const CheckpointMarkers = memo(function CheckpointMarkers({ routes, selectedRouteId }: CheckpointMarkersProps) {
  const ordered = [...routes].sort(
    (a, b) => Number(a.id === selectedRouteId) - Number(b.id === selectedRouteId),
  )
  return ordered.flatMap((route) => {
    const selected = route.id === selectedRouteId
    const visible = selected ? route.checkpoints : route.checkpoints.filter((c) => c.risk !== 'low')
    return visible.map((checkpoint) => (
      <CircleMarker
        key={`${route.id}-${checkpoint.sequence}-${selected}`}
        center={[checkpoint.lat, checkpoint.lon]}
        radius={selected ? 4.5 : 4}
        pathOptions={{
          color: '#ffffff',
          weight: 1.5,
          fillColor: RISK_META[checkpoint.risk].color,
          fillOpacity: selected ? 1 : 0.75,
        }}
      >
        <Popup>
          <CheckpointDetails routeLabel={route.label} checkpoint={checkpoint} />
        </Popup>
      </CircleMarker>
    ))
  })
})

function Measurement({ label, value, level }: { label: string; value: string; level: RiskLevel }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-slate-500">{label}</dt>
      <dd className="flex items-center gap-1.5 font-medium text-slate-900 tabular-nums">
        {value}
        {level !== 'low' && <RiskBadge level={level} />}
      </dd>
    </div>
  )
}

function CheckpointDetails({ routeLabel, checkpoint }: { routeLabel: string; checkpoint: Checkpoint }) {
  return (
    <div className="min-w-52 text-sm">
      <div className="mb-1.5 flex items-center justify-between gap-3">
        <p className="font-semibold text-slate-900">
          Route {routeLabel} · mile {Math.round(checkpoint.distance_mi)}
        </p>
        <RiskBadge level={checkpoint.risk} />
      </div>
      <p className="mb-2 text-slate-600">ETA {formatFullDateTime(checkpoint.eta)}</p>
      <dl className="space-y-1">
        <Measurement label="Wind" value={`${checkpoint.wind_mph.toFixed(0)} mph`} level={checkpoint.factors.wind} />
        <Measurement label="Rain" value={`${checkpoint.rain_in_hr.toFixed(2)} in/hr`} level={checkpoint.factors.rain} />
        <Measurement label="Snow" value={`${checkpoint.snow_in_hr.toFixed(2)} in/hr`} level={checkpoint.factors.snow} />
      </dl>
      {checkpoint.reasons.length > 0 && (
        <ul className="mt-2 list-disc space-y-0.5 border-t border-slate-200 pt-2 pl-4 text-xs text-slate-600">
          {checkpoint.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
