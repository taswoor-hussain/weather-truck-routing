import type { RiskRaster } from './heatmapRaster'

let canvas: HTMLCanvasElement | null = null

/** Encode a raster as a PNG data URL, reusing one off-screen canvas. */
export function rasterToDataUrl(raster: RiskRaster): string {
  canvas ??= document.createElement('canvas')
  canvas.width = raster.width
  canvas.height = raster.height
  const context = canvas.getContext('2d')
  if (!context) return ''
  context.putImageData(new ImageData(new Uint8ClampedArray(raster.data), raster.width, raster.height), 0, 0)
  return canvas.toDataURL('image/png')
}
