import { memo } from 'react'
import { Polyline, Tooltip } from 'react-leaflet'

import { formatDuration, formatMiles } from '../../lib/format'
import { routeColor } from '../../lib/risk'
import type { RouteOption } from '../../types/api'

interface RouteLinesProps {
  routes: RouteOption[]
  selectedRouteId: number | null
  onSelect: (routeId: number) => void
}

/** All route options; the selected one is drawn last (on top) with a casing. */
export const RouteLines = memo(function RouteLines({ routes, selectedRouteId, onSelect }: RouteLinesProps) {
  const ordered = routes
    .map((route, index) => ({ route, color: routeColor(index) }))
    .sort((a, b) => Number(a.route.id === selectedRouteId) - Number(b.route.id === selectedRouteId))

  return ordered.map(({ route, color }) => {
    const selected = route.id === selectedRouteId
    return (
      <Polyline
        key={`${route.id}-${selected}`}
        positions={route.geometry}
        pathOptions={{ color, weight: selected ? 9 : 4, opacity: selected ? 0.85 : 0.55 }}
        eventHandlers={{ click: () => onSelect(route.id) }}
      >
        <Tooltip sticky>
          <span className="font-semibold">Route {route.label}</span>
          {route.is_recommended && ' · Recommended'}
          <br />
          {formatMiles(route.distance_mi)} · {formatDuration(route.duration_s)}
        </Tooltip>
      </Polyline>
    )
  })
})
