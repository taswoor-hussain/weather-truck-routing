import { memo, useId } from 'react'

import { usePlayback } from '../../hooks/usePlayback'
import { addHours, formatDateTime, formatFullDateTime } from '../../lib/format'
import { RISK_LEVELS, RISK_META } from '../../lib/risk'
import { positionAt } from '../../lib/routeProgress'
import type { RouteOption } from '../../types/api'
import { Spinner } from '../ui/Spinner'

const TICKS = [0, 12, 24, 36, 48]
const HOUR_MS = 3_600_000

interface ForecastPanelProps {
  startTime: string
  maxHour: number
  hour: number
  onHourChange: (hour: number) => void
  /** The selected route, whose time on the road is highlighted on the track. */
  route: RouteOption | undefined
  routeColor: string
  departureTime: string
  showHeatmap: boolean
  onShowHeatmapChange: (show: boolean) => void
  heatmapStatus: 'pending' | 'error' | 'success'
  onRetryHeatmap: () => void
}

function PlayIcon({ playing }: { playing: boolean }) {
  return playing ? (
    <svg viewBox="0 0 20 20" className="size-4" fill="currentColor" aria-hidden="true">
      <rect x="5" y="4" width="3.5" height="12" rx="1" />
      <rect x="11.5" y="4" width="3.5" height="12" rx="1" />
    </svg>
  ) : (
    <svg viewBox="0 0 20 20" className="size-4" fill="currentColor" aria-hidden="true">
      <path d="M6 4.5v11a1 1 0 0 0 1.5.86l9-5.5a1 1 0 0 0 0-1.72l-9-5.5A1 1 0 0 0 6 4.5Z" />
    </svg>
  )
}

function tripStatus(route: RouteOption, time: Date, departureTime: string): string {
  const position = positionAt(route.checkpoints, time)
  const name = `Route ${route.label}`
  switch (position?.status) {
    case 'waiting':
      return `${name} departs at ${formatDateTime(departureTime)}`
    case 'driving':
      return `${name} on the road · mile ${Math.round(position.distanceMi)} of ${Math.round(route.distance_mi)} · arrives ${formatDateTime(route.arrival_time)}`
    case 'arrived':
      return `${name} arrived at ${formatDateTime(route.arrival_time)} · weather forecast continues`
    default:
      return ''
  }
}

/**
 * 0–48 h forecast slider (hour 0 = departure hour). The forecast window is longer
 * than most trips, so the selected route's time on the road is shaded on the track.
 */
export const ForecastPanel = memo(function ForecastPanel({
  startTime,
  maxHour,
  hour,
  onHourChange,
  route,
  routeColor,
  departureTime,
  showHeatmap,
  onShowHeatmapChange,
  heatmapStatus,
  onRetryHeatmap,
}: ForecastPanelProps) {
  const sliderId = useId()
  const statusId = useId()
  const [playing, setPlaying] = usePlayback(hour, maxHour, onHourChange)
  const time = addHours(startTime, hour)

  const start = Date.parse(startTime)
  const toPercent = (iso: string) =>
    Math.min(Math.max((Date.parse(iso) - start) / HOUR_MS / maxHour, 0), 1) * 100
  const tripFrom = toPercent(departureTime)
  const tripTo = route ? toPercent(route.arrival_time) : tripFrom
  const progress = (hour / maxHour) * 100

  const togglePlay = () => {
    if (!playing && hour >= maxHour) onHourChange(0)
    setPlaying(!playing)
  }

  return (
    <div className="pointer-events-auto rounded-2xl bg-white/95 px-3 py-2.5 shadow-lg ring-1 ring-slate-200 backdrop-blur sm:px-4 sm:py-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <button
          type="button"
          onClick={togglePlay}
          aria-label={playing ? 'Pause forecast animation' : 'Play forecast animation'}
          className="grid size-9 shrink-0 place-items-center rounded-full bg-blue-700 text-white hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
        >
          <PlayIcon playing={playing} />
        </button>
        <div className="min-w-0 flex-1">
          <label htmlFor={sliderId} className="block text-xs font-medium text-slate-500">
            Departure + {hour} h
          </label>
          <p className="text-sm font-semibold text-slate-900 tabular-nums" aria-live="polite">
            {formatFullDateTime(time)}
          </p>
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={showHeatmap}
            onChange={(event) => onShowHeatmapChange(event.target.checked)}
            className="size-4 rounded accent-blue-700"
          />
          Weather heatmap
          {heatmapStatus === 'pending' && showHeatmap && <Spinner className="size-4 text-slate-400" />}
        </label>
      </div>

      {route && (
        <p id={statusId} className="mt-1.5 flex items-center gap-1.5 text-xs text-slate-600">
          <span className="h-2 w-3 shrink-0 rounded-sm opacity-80" style={{ backgroundColor: routeColor }} aria-hidden="true" />
          <span className="truncate">{tripStatus(route, time, departureTime)}</span>
        </p>
      )}

      {/* Track layers sit under a transparent range input, inset by half the thumb width
          so percentages line up with the thumb's centre. */}
      <div className="relative mt-2 h-5">
        <div className="absolute inset-x-[9px] top-1/2 h-2 -translate-y-1/2 overflow-hidden rounded-full bg-slate-200">
          {/* Elapsed forecast time (neutral), then the trip window in the route colour on top. */}
          <div className="absolute inset-y-0 left-0 bg-slate-400/50" style={{ width: `${progress}%` }} />
          <div
            className="absolute inset-y-0 rounded-full opacity-80"
            style={{ left: `${tripFrom}%`, width: `${Math.max(tripTo - tripFrom, 0.8)}%`, backgroundColor: routeColor }}
            title={route ? `Route ${route.label} on the road` : undefined}
          />
        </div>
        {route && tripTo < 100 && (
          <div
            className="absolute top-0 bottom-0 w-0.5 rounded-full"
            style={{ left: `calc(9px + (100% - 18px) * ${tripTo / 100})`, backgroundColor: routeColor }}
            aria-hidden="true"
          />
        )}
        <input
          id={sliderId}
          type="range"
          min={0}
          max={maxHour}
          step={1}
          value={hour}
          onChange={(event) => {
            setPlaying(false)
            onHourChange(Number(event.target.value))
          }}
          aria-describedby={route ? statusId : undefined}
          aria-valuetext={`Departure plus ${hour} hours, ${formatFullDateTime(time)}`}
          className="forecast-range absolute inset-0"
        />
      </div>
      <div className="mx-[9px] hidden justify-between text-[10px] text-slate-400 tabular-nums sm:flex" aria-hidden="true">
        {TICKS.map((tick) => (
          <span key={tick}>{tick} h</span>
        ))}
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-slate-100 pt-2 text-[11px] text-slate-600 sm:text-xs">
        {heatmapStatus === 'error' ? (
          <span className="text-red-700">
            Heatmap unavailable.{' '}
            <button type="button" onClick={onRetryHeatmap} className="font-semibold underline">
              Retry
            </button>
          </span>
        ) : (
          RISK_LEVELS.map((level) => (
            <span key={level} className="inline-flex items-center gap-1.5">
              <span className="size-2.5 rounded-sm" style={{ backgroundColor: RISK_META[level].color }} />
              {RISK_META[level].label}
            </span>
          ))
        )}
      </div>
    </div>
  )
})
