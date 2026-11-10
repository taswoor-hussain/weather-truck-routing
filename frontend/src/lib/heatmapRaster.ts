import type { Heatmap } from '../types/api'
import { RISK_META, RISK_LEVELS } from './risk'

/** Pixels per grid cell; the browser scales the image further when drawing it. */
export const RASTER_SCALE = 8

/** Opacity per risk score, so calm areas stay subtle and hazards stand out. */
const ALPHA_BY_SCORE = [0.16, 0.42, 0.55, 0.65, 0.75]

export interface RiskRaster {
  width: number
  height: number
  data: Uint8ClampedArray
}

/** Risk score per grid cell for one hour (`NaN` outside the corridor). */
export function gridValues(heatmap: Heatmap, hour: number): Float32Array {
  const values = new Float32Array(heatmap.rows * heatmap.cols).fill(Number.NaN)
  for (const cell of heatmap.cells) {
    values[cell.row * heatmap.cols + cell.col] = cell.risk[hour] ?? Number.NaN
  }
  return values
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t
}

/** Colour and alpha for a continuous score in [0, 4]. */
export function colorForScore(score: number): [number, number, number, number] {
  const clamped = Math.min(Math.max(score, 0), RISK_LEVELS.length - 1)
  const low = Math.floor(clamped)
  const high = Math.min(low + 1, RISK_LEVELS.length - 1)
  const t = clamped - low
  const a = RISK_META[RISK_LEVELS[low]].rgb
  const b = RISK_META[RISK_LEVELS[high]].rgb
  return [
    lerp(a[0], b[0], t),
    lerp(a[1], b[1], t),
    lerp(a[2], b[2], t),
    lerp(ALPHA_BY_SCORE[low], ALPHA_BY_SCORE[high], t),
  ]
}

const LUT_STEPS_PER_LEVEL = 64
const LUT_SIZE = (RISK_LEVELS.length - 1) * LUT_STEPS_PER_LEVEL + 1

/** Precomputed RGBA for quantised scores, so the per-pixel loop never allocates. */
const COLOR_LUT: Uint8ClampedArray = (() => {
  const lut = new Uint8ClampedArray(LUT_SIZE * 4)
  for (let i = 0; i < LUT_SIZE; i++) {
    const [r, g, b, a] = colorForScore(i / LUT_STEPS_PER_LEVEL)
    lut.set([r, g, b, a * 255], i * 4)
  }
  return lut
})()

/**
 * Upsample the grid with bilinear interpolation *in risk space* (then colour),
 * so transitions read as risk gradients rather than muddy colour blends.
 * Missing neighbours are skipped and fade the edge of the corridor.
 */
export function rasterizeRisk(heatmap: Heatmap, hour: number, scale = RASTER_SCALE): RiskRaster {
  const { rows, cols } = heatmap
  const values = gridValues(heatmap, hour)
  const width = cols * scale
  const height = rows * scale
  const data = new Uint8ClampedArray(width * height * 4)

  let sum = 0
  let weight = 0
  const accumulate = (row: number, col: number, w: number) => {
    if (w <= 0 || row < 0 || col < 0 || row >= rows || col >= cols) return
    const v = values[row * cols + col]
    if (!Number.isNaN(v)) {
      sum += v * w
      weight += w
    }
  }

  for (let y = 0; y < height; y++) {
    // Position in cell-centre coordinates.
    const gy = (y + 0.5) / scale - 0.5
    const row = Math.floor(gy)
    const ty = gy - row
    for (let x = 0; x < width; x++) {
      const gx = (x + 0.5) / scale - 0.5
      const col = Math.floor(gx)
      const tx = gx - col

      sum = 0
      weight = 0
      accumulate(row, col, (1 - tx) * (1 - ty))
      accumulate(row, col + 1, tx * (1 - ty))
      accumulate(row + 1, col, (1 - tx) * ty)
      accumulate(row + 1, col + 1, tx * ty)
      if (weight === 0) continue

      const lutIndex = Math.round((sum / weight) * LUT_STEPS_PER_LEVEL) * 4
      const offset = (y * width + x) * 4
      data[offset] = COLOR_LUT[lutIndex]
      data[offset + 1] = COLOR_LUT[lutIndex + 1]
      data[offset + 2] = COLOR_LUT[lutIndex + 2]
      // Partial coverage near the corridor edge fades out smoothly.
      data[offset + 3] = COLOR_LUT[lutIndex + 3] * Math.min(weight * 1.6, 1)
    }
  }
  return { width, height, data }
}
