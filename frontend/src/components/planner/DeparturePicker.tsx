import { useCallback, useEffect, useId, useRef, useState } from 'react'

import { useDismiss } from '../../hooks/useDismiss'
import {
  departureDays,
  formatDeparture,
  isSameDay,
  moveToDay,
  roundUpToSlot,
  timeSlots,
} from '../../lib/departure'

interface DeparturePickerProps {
  id: string
  value: Date
  onChange: (date: Date) => void
  invalid?: boolean
  describedBy?: string
}

const weekdayFormat = new Intl.DateTimeFormat(undefined, { weekday: 'short' })
const monthFormat = new Intl.DateTimeFormat(undefined, { month: 'short' })
const longFormat = new Intl.DateTimeFormat(undefined, {
  weekday: 'long',
  month: 'long',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

function CalendarIcon() {
  return (
    <svg viewBox="0 0 20 20" className="size-4 shrink-0 text-slate-400" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <rect x="3" y="4.5" width="14" height="12.5" rx="2" />
      <path d="M3 8.5h14M7 2.5v4M13 2.5v4" strokeLinecap="round" />
    </svg>
  )
}

function presets(now: Date) {
  const tomorrowAt = (hour: number) => {
    const date = new Date(now)
    date.setDate(date.getDate() + 1)
    date.setHours(hour, 0, 0, 0)
    return date
  }
  return [
    { label: 'Now', date: now },
    { label: 'In 1 hour', date: roundUpToSlot(new Date(now.getTime() + 3_600_000)) },
    { label: 'Tomorrow 6 AM', date: tomorrowAt(6) },
  ]
}

/**
 * Departure picker for the 7-day forecast window: quick presets, a row of the
 * eight valid days and 30-minute time slots (past slots disabled). No typing needed.
 */
export function DeparturePicker({ id, value, onChange, invalid, describedBy }: DeparturePickerProps) {
  const dialogId = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const slotsRef = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  // "Now" is captured when the picker opens so rendering stays pure.
  const [now, setNow] = useState(() => new Date())

  const close = useCallback((restoreFocus = true) => {
    setOpen(false)
    if (restoreFocus) triggerRef.current?.focus()
  }, [])
  const dismiss = useCallback(() => close(false), [close])
  useDismiss(rootRef, open, dismiss)

  // Bring the selected time into view when the picker opens or the day changes.
  useEffect(() => {
    if (!open) return
    const selected = slotsRef.current?.querySelector<HTMLElement>('[aria-pressed="true"]')
    if (selected && slotsRef.current) {
      slotsRef.current.scrollTop = selected.offsetTop - slotsRef.current.clientHeight / 2 + selected.clientHeight / 2
    }
  }, [open, value])

  const toggle = () => {
    if (!open) setNow(new Date())
    setOpen(!open)
  }

  const choose = (date: Date, closeAfter: boolean) => {
    onChange(date)
    if (closeAfter) close()
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={triggerRef}
        id={id}
        type="button"
        onClick={toggle}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? dialogId : undefined}
        aria-invalid={invalid}
        aria-describedby={describedBy}
        className={`flex w-full items-center gap-2 rounded-lg bg-white px-3 py-2 text-left text-sm text-slate-900 shadow-sm ring-1 ring-inset focus:ring-2 focus:ring-blue-600 focus:outline-none ${
          invalid ? 'ring-red-500' : open ? 'ring-2 ring-blue-600' : 'ring-slate-300 hover:ring-slate-400'
        }`}
      >
        <CalendarIcon />
        <span className="truncate">{formatDeparture(value, now)}</span>
      </button>

      {open && (
        <div
          id={dialogId}
          role="dialog"
          aria-label="Choose departure time"
          className="absolute top-full left-0 z-[1100] mt-2 w-[22rem] max-w-[calc(100vw-2.5rem)] rounded-xl bg-white p-3 shadow-xl ring-1 ring-slate-200"
        >
          <div className="flex flex-wrap gap-1.5">
            {presets(now).map((preset) => (
              <button
                key={preset.label}
                type="button"
                onClick={() => choose(preset.date, true)}
                className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-blue-50 hover:text-blue-800 focus-visible:outline-2 focus-visible:outline-blue-700"
              >
                {preset.label}
              </button>
            ))}
          </div>

          <p className="mt-3 mb-1.5 text-[11px] font-semibold tracking-wide text-slate-500 uppercase">Day</p>
          <div className="grid grid-cols-8 gap-1">
            {departureDays(now).map((day, index) => {
              const selected = isSameDay(day, value)
              return (
                <button
                  key={day.toISOString()}
                  type="button"
                  aria-pressed={selected}
                  aria-label={day.toDateString()}
                  autoFocus={selected}
                  onClick={() => choose(moveToDay(value, day, now), false)}
                  className={`flex flex-col items-center rounded-lg py-1.5 transition-colors focus-visible:outline-2 focus-visible:outline-blue-700 ${
                    selected ? 'bg-blue-700 text-white shadow-sm' : 'text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  <span className={`text-[10px] uppercase ${selected ? 'text-blue-100' : 'text-slate-400'}`}>
                    {index === 0 ? 'Today' : weekdayFormat.format(day)}
                  </span>
                  <span className="text-sm font-semibold tabular-nums">{day.getDate()}</span>
                  <span className={`text-[10px] ${selected ? 'text-blue-100' : 'text-slate-400'}`}>
                    {monthFormat.format(day)}
                  </span>
                </button>
              )
            })}
          </div>

          <p className="mt-3 mb-1.5 text-[11px] font-semibold tracking-wide text-slate-500 uppercase">Time</p>
          <div ref={slotsRef} className="relative grid max-h-44 grid-cols-4 gap-1 overflow-y-auto pr-1">
            {timeSlots(value, now).map((slot) => {
              const selected = slot.date.getTime() === value.getTime()
              return (
                <button
                  key={slot.label}
                  type="button"
                  disabled={slot.disabled}
                  aria-pressed={selected}
                  onClick={() => choose(slot.date, true)}
                  className={`rounded-md py-1.5 text-xs tabular-nums transition-colors focus-visible:outline-2 focus-visible:outline-blue-700 disabled:cursor-not-allowed disabled:text-slate-300 ${
                    selected
                      ? 'bg-blue-700 font-semibold text-white'
                      : 'text-slate-700 hover:bg-slate-100 disabled:hover:bg-transparent'
                  }`}
                >
                  {slot.label}
                </button>
              )
            })}
          </div>

          <div className="mt-3 flex items-center justify-between gap-3 border-t border-slate-100 pt-3">
            <p className="text-xs text-slate-600">{longFormat.format(value)}</p>
            <button
              type="button"
              onClick={() => close()}
              className="rounded-lg bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
