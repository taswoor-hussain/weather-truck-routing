import { latLngBounds } from 'leaflet'
import { memo, useMemo } from 'react'
import { ImageOverlay } from 'react-leaflet'

import { rasterToDataUrl } from '../../lib/heatmapImage'
import { rasterizeRisk } from '../../lib/heatmapRaster'
import type { Heatmap } from '../../types/api'
import { HEATMAP_PANE } from './TripMap'

/** Rendered frames per heatmap and hour, so scrubbing back and forth is instant. */
const frameCache = new WeakMap<Heatmap, Map<number, string>>()

function frameFor(heatmap: Heatmap, hour: number): string {
  let frames = frameCache.get(heatmap)
  if (!frames) {
    frames = new Map()
    frameCache.set(heatmap, frames)
  }
  let url = frames.get(hour)
  if (url === undefined) {
    url = rasterToDataUrl(rasterizeRisk(heatmap, hour))
    frames.set(hour, url)
  }
  return url
}

/** Corridor risk for one forecast hour, drawn as a single smoothed image. */
export const HeatmapLayer = memo(function HeatmapLayer({ heatmap, hour }: { heatmap: Heatmap; hour: number }) {
  const url = useMemo(() => frameFor(heatmap, hour), [heatmap, hour])
  const bounds = useMemo(() => {
    const { south, west, north, east } = heatmap.bounds
    return latLngBounds([south, west], [north, east])
  }, [heatmap])

  return <ImageOverlay url={url} bounds={bounds} pane={HEATMAP_PANE} interactive={false} />
})
