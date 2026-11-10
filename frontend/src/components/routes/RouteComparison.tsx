import { memo } from 'react'

import { routeColor } from '../../lib/risk'
import type { Trip } from '../../types/api'
import { Alert } from '../ui/Alert'
import { RouteCard } from './RouteCard'

interface RouteComparisonProps {
  trip: Trip
  selectedRouteId: number | null
  onSelectRoute: (routeId: number) => void
}

export const RouteComparison = memo(function RouteComparison({
  trip,
  selectedRouteId,
  onSelectRoute,
}: RouteComparisonProps) {
  const recommended = trip.routes.find((route) => route.id === trip.recommendation.route_id)

  return (
    <section aria-labelledby="routes-heading" className="space-y-3">
      <div>
        <h2 id="routes-heading" className="text-sm font-semibold text-slate-900">
          {trip.routes.length} route {trip.routes.length === 1 ? 'option' : 'options'}
        </h2>
        <p className="text-xs text-slate-500">
          {trip.origin.label} → {trip.destination.label}
        </p>
      </div>

      {recommended && (
        <Alert tone="info" title={`Recommended: Route ${recommended.label}`}>
          {trip.recommendation.reason}
        </Alert>
      )}
      {trip.recommendation.advisory && <Alert tone="warning">{trip.recommendation.advisory}</Alert>}

      <div className="space-y-2.5">
        {trip.routes.map((route, index) => (
          <RouteCard
            key={route.id}
            route={route}
            color={routeColor(index)}
            selected={route.id === selectedRouteId}
            onSelect={onSelectRoute}
          />
        ))}
      </div>

      <p className="text-xs leading-relaxed text-slate-500">
        Ranking: fewest No Travel → Severe → High miles, then lowest average risk, then shortest
        drive time. Each checkpoint covers the road half-way to its neighbours.
      </p>
    </section>
  )
})
