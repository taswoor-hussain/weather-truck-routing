import { memo } from 'react'
import { CircleMarker, Tooltip } from 'react-leaflet'

import type { Place } from '../../types/api'

const ENDPOINT_STYLE = { color: '#0f172a', weight: 3, fillColor: '#ffffff', fillOpacity: 1 }

export const EndpointMarkers = memo(function EndpointMarkers({
  origin,
  destination,
}: {
  origin: Place
  destination: Place
}) {
  return [
    { place: origin, role: 'Origin' },
    { place: destination, role: 'Destination' },
  ].map(({ place, role }) => (
    <CircleMarker key={role} center={[place.lat, place.lon]} radius={8} pathOptions={ENDPOINT_STYLE}>
      <Tooltip direction="top" offset={[0, -8]}>
        <span className="font-semibold">{role}:</span> {place.label}
      </Tooltip>
    </CircleMarker>
  ))
})
