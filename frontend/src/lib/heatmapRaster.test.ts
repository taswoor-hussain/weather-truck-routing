import { describe, expect, it } from 'vitest'

import type { Heatmap } from '../types/api'
import { colorForScore, gridValues, rasterizeRisk } from './heatmapRaster'
import { RISK_META } from './risk'

const heatmap: Heatmap = {
  bounds: { south: 0, west: 0, north: 1, east: 2 },
  rows: 1,
  cols: 3,
  start_time: '2026-11-10T14:00:00Z',
  hours: 2,
  cells: [
    { row: 0, col: 0, risk: [0, 4] },
    { row: 0, col: 1, risk: [4, 4] },
    // col 2 is outside the corridor
  ],
}

const pixel = (raster: ReturnType<typeof rasterizeRisk>, x: number, y = 0) =>
  Array.from(raster.data.slice((y * raster.width + x) * 4, (y * raster.width + x) * 4 + 4))

describe('gridValues', () => {
  it('places each cell by row/col and marks missing cells as NaN', () => {
    const values = gridValues(heatmap, 0)
    expect(values[0]).toBe(0)
    expect(values[1]).toBe(4)
    expect(Number.isNaN(values[2])).toBe(true)
  })
})

describe('colorForScore', () => {
  it('matches the risk palette at whole scores', () => {
    expect(colorForScore(3).slice(0, 3)).toEqual(RISK_META.severe.rgb)
    expect(colorForScore(10).slice(0, 3)).toEqual(RISK_META.no_travel.rgb)
  })

  it('becomes more opaque as risk rises', () => {
    expect(colorForScore(0)[3]).toBeLessThan(colorForScore(4)[3])
  })
})

describe('rasterizeRisk', () => {
  const scale = 4
  const raster = rasterizeRisk(heatmap, 0, scale)

  it('upsamples the grid by the scale factor', () => {
    expect(raster.width).toBe(12)
    expect(raster.height).toBe(4)
    expect(raster.data).toHaveLength(12 * 4 * 4)
  })

  it('interpolates between cell centres in risk space', () => {
    const left = pixel(raster, 1, 1)
    const middle = pixel(raster, 4, 1)
    const right = pixel(raster, 6, 1)
    expect(left[0]).toBeLessThan(middle[0])
    expect(middle[3]).toBeGreaterThan(left[3])
    expect(right.slice(0, 3)).toEqual(RISK_META.no_travel.rgb)
  })

  it('leaves cells outside the corridor transparent', () => {
    expect(pixel(raster, 11, 1)[3]).toBe(0)
  })

  it('renders the requested hour', () => {
    const later = rasterizeRisk(heatmap, 1, scale)
    expect(pixel(later, 1, 1).slice(0, 3)).toEqual(RISK_META.no_travel.rgb)
  })
})
