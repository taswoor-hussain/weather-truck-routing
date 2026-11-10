import { describe, expect, it } from 'vitest'

import { formatDuration, formatMiles, formatWeight, nextFullHour, toDateTimeLocalValue } from './format'

describe('format', () => {
  it('formats durations in hours and minutes', () => {
    expect(formatDuration(45 * 60)).toBe('45 min')
    expect(formatDuration(15 * 3600 + 5 * 60)).toBe('15 h 05 min')
    expect(formatDuration(59.6 * 60)).toBe('1 h 00 min')
  })

  it('formats miles and weight with separators', () => {
    expect(formatMiles(1017.4)).toBe('1,017 mi')
    expect(formatWeight(42000)).toBe('42,000 lb')
  })

  it('produces datetime-local values in local time', () => {
    const date = new Date(2026, 10, 9, 7, 5)
    expect(toDateTimeLocalValue(date)).toBe('2026-11-09T07:05')
  })

  it('rounds up to the next full hour', () => {
    const next = nextFullHour(new Date(2026, 10, 9, 7, 5, 30))
    expect([next.getHours(), next.getMinutes(), next.getSeconds()]).toEqual([8, 0, 0])
  })
})
