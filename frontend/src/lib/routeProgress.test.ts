import { describe, expect, it } from 'vitest'

import type { Checkpoint } from '../types/api'
import { positionAt } from './routeProgress'

const checkpoint = (sequence: number, distance: number, lon: number, eta: string): Checkpoint => ({
  sequence,
  distance_mi: distance,
  lat: 35,
  lon,
  eta,
  wind_mph: 0,
  rain_in_hr: 0,
  snow_in_hr: 0,
  risk: 'low',
  factors: { wind: 'low', rain: 'low', snow: 'low' },
  reasons: [],
})

const checkpoints = [
  checkpoint(0, 0, -100, '2026-11-10T14:00:00Z'),
  checkpoint(1, 50, -99, '2026-11-10T15:00:00Z'),
  checkpoint(2, 100, -98, '2026-11-10T17:00:00Z'),
]

describe('positionAt', () => {
  it('waits at the origin before departure', () => {
    expect(positionAt(checkpoints, new Date('2026-11-10T13:00:00Z'))).toMatchObject({
      lon: -100,
      status: 'waiting',
    })
  })

  it('interpolates between the bracketing checkpoints', () => {
    const position = positionAt(checkpoints, new Date('2026-11-10T16:00:00Z'))
    expect(position).toMatchObject({ lon: -98.5, distanceMi: 75, status: 'driving' })
  })

  it('stays at the destination after arrival', () => {
    expect(positionAt(checkpoints, new Date('2026-11-11T00:00:00Z'))).toMatchObject({
      lon: -98,
      status: 'arrived',
    })
  })

  it('handles routes without checkpoints', () => {
    expect(positionAt([], new Date())).toBeNull()
  })
})
