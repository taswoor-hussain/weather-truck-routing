import type { Checkpoint } from '../types/api'

export interface TruckPosition {
  lat: number
  lon: number
  /** Miles driven at this time. */
  distanceMi: number
  status: 'waiting' | 'driving' | 'arrived'
}

/**
 * Where the truck is at `time`, interpolated between the checkpoints whose ETAs
 * bracket it. Checkpoints are at most 50 mi apart, which is precise enough for a
 * position marker.
 */
export function positionAt(checkpoints: Checkpoint[], time: Date): TruckPosition | null {
  if (checkpoints.length === 0) return null
  const t = time.getTime()
  const first = checkpoints[0]
  const last = checkpoints[checkpoints.length - 1]

  if (t <= Date.parse(first.eta)) {
    return { lat: first.lat, lon: first.lon, distanceMi: 0, status: 'waiting' }
  }
  if (t >= Date.parse(last.eta)) {
    return { lat: last.lat, lon: last.lon, distanceMi: last.distance_mi, status: 'arrived' }
  }

  // Binary search for the last checkpoint reached by time t.
  let lo = 0
  let hi = checkpoints.length - 1
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1
    if (Date.parse(checkpoints[mid].eta) <= t) lo = mid
    else hi = mid
  }
  const a = checkpoints[lo]
  const b = checkpoints[hi]
  const start = Date.parse(a.eta)
  const span = Date.parse(b.eta) - start
  const f = span > 0 ? (t - start) / span : 0
  return {
    lat: a.lat + (b.lat - a.lat) * f,
    lon: a.lon + (b.lon - a.lon) * f,
    distanceMi: a.distance_mi + (b.distance_mi - a.distance_mi) * f,
    status: 'driving',
  }
}
