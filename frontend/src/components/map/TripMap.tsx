import type { ReactNode } from 'react'
import { MapContainer, Pane, TileLayer, ZoomControl } from 'react-leaflet'

const CONTINENTAL_US_CENTER: [number, number] = [39.5, -98.35]
const ESRI_CANVAS = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas'
const ATTRIBUTION = 'Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors'

/**
 * Stacking order (Leaflet panes): basemap → heatmap (350) → routes & checkpoints
 * (overlay, 400) → place labels (450) → truck markers (marker pane, 600).
 */
export const HEATMAP_PANE = 'heatmap'

interface TripMapProps {
  children?: ReactNode
}

/** Base map with a muted canvas so risk colours stand out; trip layers are children. */
export function TripMap({ children }: TripMapProps) {
  return (
    <MapContainer
      center={CONTINENTAL_US_CENTER}
      zoom={4}
      minZoom={3}
      maxZoom={16}
      preferCanvas
      zoomControl={false}
      worldCopyJump
      className="h-full w-full bg-slate-200"
    >
      <TileLayer url={`${ESRI_CANVAS}/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`} attribution={ATTRIBUTION} />
      <Pane name={HEATMAP_PANE} style={{ zIndex: 350 }} />
      <Pane name="labels" style={{ zIndex: 450, pointerEvents: 'none' }}>
        <TileLayer url={`${ESRI_CANVAS}/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}`} />
      </Pane>
      <ZoomControl position="topright" />
      {children}
    </MapContainer>
  )
}
