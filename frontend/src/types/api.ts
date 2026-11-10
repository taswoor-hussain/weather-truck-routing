/** API contracts. Mirrors backend/trips/serializers.py. */

export type RiskLevel = 'low' | 'moderate' | 'high' | 'severe' | 'no_travel'

export type CheckpointInterval = 10 | 25 | 50

export interface Place {
  label: string
  lat: number
  lon: number
}

export interface Checkpoint {
  sequence: number
  distance_mi: number
  lat: number
  lon: number
  eta: string
  wind_mph: number
  rain_in_hr: number
  snow_in_hr: number
  risk: RiskLevel
  factors: Record<'wind' | 'rain' | 'snow', RiskLevel>
  reasons: string[]
}

export interface RouteOption {
  id: number
  label: string
  summary: string
  rank: number
  is_recommended: boolean
  distance_mi: number
  duration_s: number
  arrival_time: string
  average_risk: number
  risk_miles: Record<RiskLevel, number>
  geometry: [number, number][]
  checkpoints: Checkpoint[]
}

export interface Trip {
  id: string
  origin: Place
  destination: Place
  departure_time: string
  load_weight_lb: number
  checkpoint_interval_mi: CheckpointInterval
  recommendation: {
    route_id: number | null
    reason: string
    advisory: string
  }
  routes: RouteOption[]
  created_at: string
}

export interface TripRequest {
  origin: Place
  destination: Place
  departure_time: string
  load_weight_lb: number
  checkpoint_interval_mi: CheckpointInterval
}

export interface HeatmapCell {
  row: number
  col: number
  /** Risk score (0 = low … 4 = no travel) per hour from start_time. */
  risk: number[]
}

export interface Heatmap {
  bounds: { south: number; west: number; north: number; east: number }
  rows: number
  cols: number
  start_time: string
  hours: number
  cells: HeatmapCell[]
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    details: Record<string, unknown>
  }
}
