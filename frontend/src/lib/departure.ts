/** Departure-time rules shared by the picker and form validation. */

export const MAX_DAYS_AHEAD = 7
export const SLOT_MINUTES = 30
/** The API accepts departures up to an hour in the past. */
const PAST_GRACE_MS = 60 * 60_000
const MINUTE_MS = 60_000
const DAY_MS = 86_400_000

export interface DepartureSlot {
  date: Date
  label: string
  disabled: boolean
}

function startOfDay(date: Date): Date {
  const day = new Date(date)
  day.setHours(0, 0, 0, 0)
  return day
}

export function isSameDay(a: Date, b: Date): boolean {
  return startOfDay(a).getTime() === startOfDay(b).getTime()
}

export function earliestDeparture(now: Date): Date {
  return new Date(now.getTime() - PAST_GRACE_MS)
}

export function latestDeparture(now: Date): Date {
  return new Date(now.getTime() + MAX_DAYS_AHEAD * DAY_MS)
}

export function isDepartureAllowed(date: Date, now: Date): boolean {
  const t = date.getTime()
  return t >= earliestDeparture(now).getTime() && t <= latestDeparture(now).getTime()
}

/** Today plus the following days inside the forecast window (8 days). */
export function departureDays(now: Date): Date[] {
  const today = startOfDay(now)
  return Array.from({ length: MAX_DAYS_AHEAD + 1 }, (_, i) => {
    const day = new Date(today)
    day.setDate(today.getDate() + i)
    return day
  })
}

const timeFormat = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' })

/** Every 30-minute slot of `day`, with slots outside the allowed window disabled. */
export function timeSlots(day: Date, now: Date): DepartureSlot[] {
  const base = startOfDay(day)
  const slotsPerDay = (24 * 60) / SLOT_MINUTES
  return Array.from({ length: slotsPerDay }, (_, i) => {
    const date = new Date(base)
    date.setMinutes(i * SLOT_MINUTES)
    return { date, label: timeFormat.format(date), disabled: !isDepartureAllowed(date, now) }
  })
}

/** Keep the time of day when switching days, clamped into the allowed window. */
export function moveToDay(current: Date, day: Date, now: Date): Date {
  const next = new Date(day)
  next.setHours(current.getHours(), current.getMinutes(), 0, 0)
  if (next < earliestDeparture(now)) return roundUpToSlot(now)
  const latest = latestDeparture(now)
  if (next > latest) return floorToSlot(latest)
  return next
}

export function roundUpToSlot(date: Date): Date {
  const slotMs = SLOT_MINUTES * MINUTE_MS
  return new Date(Math.ceil(date.getTime() / slotMs) * slotMs)
}

function floorToSlot(date: Date): Date {
  const slotMs = SLOT_MINUTES * MINUTE_MS
  return new Date(Math.floor(date.getTime() / slotMs) * slotMs)
}

const dayLabelFormat = new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric' })

/** "Today", "Tomorrow" or "Wed, Nov 12". */
export function relativeDayLabel(date: Date, now: Date): string {
  const diff = Math.round((startOfDay(date).getTime() - startOfDay(now).getTime()) / DAY_MS)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Tomorrow'
  return dayLabelFormat.format(date)
}

/** "Today, 3:00 PM". */
export function formatDeparture(date: Date, now: Date): string {
  return `${relativeDayLabel(date, now)}, ${timeFormat.format(date)}`
}

/** "now", "in 45 min", "in 3 h", "in 2 days". */
export function formatFromNow(date: Date, now: Date): string {
  const minutes = Math.round((date.getTime() - now.getTime()) / MINUTE_MS)
  if (Math.abs(minutes) < 5) return 'now'
  if (minutes < 0) return `${-minutes} min ago`
  if (minutes < 60) return `in ${minutes} min`
  const hours = Math.round(minutes / 60)
  if (hours < 48) return `in ${hours} h`
  return `in ${Math.round(hours / 24)} days`
}
