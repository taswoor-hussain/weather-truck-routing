import { divIcon, type DivIcon } from 'leaflet'
import { memo } from 'react'
import { Marker, Tooltip } from 'react-leaflet'

import { routeColor } from '../../lib/risk'
import { positionAt, type TruckPosition } from '../../lib/routeProgress'
import type { RouteOption } from '../../types/api'

const icons = new Map<string, DivIcon>()

function truckIcon(label: string, color: string, selected: boolean): DivIcon {
  const key = `${label}|${color}|${selected}`
  let icon = icons.get(key)
  if (!icon) {
    const size = selected ? 28 : 22
    icon = divIcon({
      className: '',
      html: `<div class="truck-pin${selected ? ' truck-pin--selected' : ''}" style="--pin-color:${color}">${label}</div>`,
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    })
    icons.set(key, icon)
  }
  return icon
}

const STATUS_TEXT: Record<TruckPosition['status'], string> = {
  waiting: 'not departed yet',
  driving: 'en route',
  arrived: 'arrived',
}

interface TruckMarkersProps {
  routes: RouteOption[]
  time: Date
  selectedRouteId: number | null
}

/** Where the truck would be on each route at the forecast time on the slider. */
export const TruckMarkers = memo(function TruckMarkers({ routes, time, selectedRouteId }: TruckMarkersProps) {
  return routes.map((route, index) => {
    const position = positionAt(route.checkpoints, time)
    if (!position) return null
    const selected = route.id === selectedRouteId
    return (
      <Marker
        key={route.id}
        position={[position.lat, position.lon]}
        icon={truckIcon(route.label, routeColor(index), selected)}
        zIndexOffset={selected ? 1000 : 0}
        keyboard={false}
      >
        <Tooltip direction="top" offset={[0, -12]}>
          Route {route.label}: mile {Math.round(position.distanceMi)}, {STATUS_TEXT[position.status]}
        </Tooltip>
      </Marker>
    )
  })
})
