import type { RiskLevel } from '../types/api'

interface RiskMeta {
  label: string
  score: number
  /** Map/marker colour. */
  color: string
  /** RGB triple for raster rendering. */
  rgb: [number, number, number]
  /** Tailwind classes for badges. */
  badgeClass: string
}

/** Ordered from safest to most dangerous; index === score. */
export const RISK_LEVELS: readonly RiskLevel[] = ['low', 'moderate', 'high', 'severe', 'no_travel']

export const RISK_META: Record<RiskLevel, RiskMeta> = {
  low: {
    label: 'Low',
    score: 0,
    color: '#16a34a',
    rgb: [22, 163, 74],
    badgeClass: 'bg-green-100 text-green-800 ring-green-600/20',
  },
  moderate: {
    label: 'Moderate',
    score: 1,
    color: '#eab308',
    rgb: [234, 179, 8],
    badgeClass: 'bg-yellow-100 text-yellow-800 ring-yellow-600/30',
  },
  high: {
    label: 'High',
    score: 2,
    color: '#f97316',
    rgb: [249, 115, 22],
    badgeClass: 'bg-orange-100 text-orange-800 ring-orange-600/30',
  },
  severe: {
    label: 'Severe',
    score: 3,
    color: '#dc2626',
    rgb: [220, 38, 38],
    badgeClass: 'bg-red-100 text-red-800 ring-red-600/30',
  },
  no_travel: {
    label: 'No Travel',
    score: 4,
    color: '#7f1d1d',
    rgb: [127, 29, 29],
    badgeClass: 'bg-red-950 text-red-50 ring-red-950',
  },
}

export function riskFromScore(score: number): RiskLevel {
  const index = Math.min(Math.max(Math.round(score), 0), RISK_LEVELS.length - 1)
  return RISK_LEVELS[index]
}

/** Distinct, risk-neutral colours for route lines (A, B, C…). */
const ROUTE_COLORS = ['#2563eb', '#0d9488', '#7c3aed', '#db2777']

export function routeColor(index: number): string {
  return ROUTE_COLORS[index % ROUTE_COLORS.length]
}
