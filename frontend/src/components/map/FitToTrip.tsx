import { latLngBounds } from 'leaflet'
import { useEffect } from 'react'
import { useMap } from 'react-leaflet'

import type { Trip } from '../../types/api'

/** Frame all routes whenever a different trip is shown (trip objects are cached per id). */
export function FitToTrip({ trip }: { trip: Trip }) {
  const map = useMap()
  useEffect(() => {
    const points = trip.routes.flatMap((route) => route.geometry)
    if (points.length) map.fitBounds(latLngBounds(points), { padding: [48, 48] })
  }, [map, trip])
  return null
}
