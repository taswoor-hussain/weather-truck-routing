import { memo, useId } from 'react'

import { usePlayback } from '../../hooks/usePlayback'
import { addHours, formatFullDateTime } from '../../lib/format'
import { RISK_LEVELS, RISK_META } from '../../lib/risk'
import { Spinner } from '../ui/Spinner'

const TICKS = [0, 12, 24, 36, 48]

interface ForecastPanelProps {
  startTime: string
  maxHour: number
  hour: number
  onHourChange: (hour: number) => void
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

/** 0–48 h forecast slider (hour 0 = departure) with heatmap toggle and legend. */
export const ForecastPanel = memo(function ForecastPanel({
  startTime,
  maxHour,
  hour,
  onHourChange,
  showHeatmap,
  onShowHeatmapChange,
  heatmapStatus,
  onRetryHeatmap,
}: ForecastPanelProps) {
  const sliderId = useId()
  const [playing, setPlaying] = usePlayback(hour, maxHour, onHourChange)
  const time = addHours(startTime, hour)

  const togglePlay = () => {
    if (!playing && hour >= maxHour) onHourChange(0)
    setPlaying(!playing)
  }

  return (
    <div className="pointer-events-auto rounded-2xl bg-white/95 px-3 py-2.5 sm:px-4 sm:py-3 shadow-lg ring-1 ring-slate-200 backdrop-blur">
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
        aria-valuetext={`Departure plus ${hour} hours, ${formatFullDateTime(time)}`}
        className="mt-2 w-full cursor-pointer accent-blue-700"
      />
      <div className="hidden justify-between text-[10px] text-slate-400 tabular-nums sm:flex" aria-hidden="true">
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
