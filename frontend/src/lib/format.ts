const numberFormat = new Intl.NumberFormat('en-US')

export function formatMiles(miles: number): string {
  return `${numberFormat.format(Math.round(miles))} mi`
}

export function formatDuration(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours === 0) return `${minutes} min`
  return `${hours} h ${String(minutes).padStart(2, '0')} min`
}

export function formatWeight(pounds: number): string {
  return `${numberFormat.format(pounds)} lb`
}

const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  hour: 'numeric',
  minute: '2-digit',
})

const fullDateTimeFormat = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

/** Short local time, e.g. "Tue 3:20 PM". */
export function formatDateTime(value: string | Date): string {
  return dateTimeFormat.format(new Date(value))
}

/** Local date and time, e.g. "Tue, Nov 10, 3:20 PM". */
export function formatFullDateTime(value: string | Date): string {
  return fullDateTimeFormat.format(new Date(value))
}

/** The next full hour after `now` (a sensible default departure). */
export function nextFullHour(now = new Date()): Date {
  const next = new Date(now)
  next.setHours(next.getHours() + 1, 0, 0, 0)
  return next
}

export function addHours(isoTime: string, hours: number): Date {
  return new Date(new Date(isoTime).getTime() + hours * 3_600_000)
}
