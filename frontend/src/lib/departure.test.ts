import { describe, expect, it } from 'vitest'

import {
  departureDays,
  formatDeparture,
  formatFromNow,
  isDepartureAllowed,
  moveToDay,
  relativeDayLabel,
  roundUpToSlot,
  timeSlots,
} from './departure'

// Tue Nov 10 2026, 14:10 local time
const NOW = new Date(2026, 10, 10, 14, 10)

describe('departure window', () => {
  it('offers today plus seven days', () => {
    const days = departureDays(NOW)
    expect(days).toHaveLength(8)
    expect(days[0].getDate()).toBe(10)
    expect(days[7].getDate()).toBe(17)
  })

  it('allows up to an hour in the past and seven days ahead', () => {
    expect(isDepartureAllowed(new Date(2026, 10, 10, 13, 15), NOW)).toBe(true)
    expect(isDepartureAllowed(new Date(2026, 10, 10, 13, 0), NOW)).toBe(false)
    expect(isDepartureAllowed(new Date(2026, 10, 17, 14, 0), NOW)).toBe(true)
    expect(isDepartureAllowed(new Date(2026, 10, 17, 14, 30), NOW)).toBe(false)
  })

  it('disables past slots today and slots beyond the window on the last day', () => {
    const today = timeSlots(NOW, NOW)
    expect(today).toHaveLength(48)
    expect(today.find((s) => s.date.getHours() === 13 && s.date.getMinutes() === 0)?.disabled).toBe(true)
    expect(today.find((s) => s.date.getHours() === 13 && s.date.getMinutes() === 30)?.disabled).toBe(false)
    const lastDay = timeSlots(new Date(2026, 10, 17), NOW)
    expect(lastDay.find((s) => s.date.getHours() === 14 && s.date.getMinutes() === 0)?.disabled).toBe(false)
    expect(lastDay.find((s) => s.date.getHours() === 15)?.disabled).toBe(true)
  })

  it('keeps the time of day when switching days, clamping into the window', () => {
    const at8am = new Date(2026, 10, 12, 8, 0)
    expect(moveToDay(at8am, new Date(2026, 10, 13), NOW)).toEqual(new Date(2026, 10, 13, 8, 0))
    // 8 AM today is too far in the past → next slot from now.
    expect(moveToDay(at8am, new Date(2026, 10, 10), NOW)).toEqual(new Date(2026, 10, 10, 14, 30))
    // 6 PM on the last day is beyond the window → latest allowed slot.
    const at6pm = new Date(2026, 10, 12, 18, 0)
    expect(moveToDay(at6pm, new Date(2026, 10, 17), NOW)).toEqual(new Date(2026, 10, 17, 14, 0))
  })

  it('rounds up to the next half hour', () => {
    expect(roundUpToSlot(NOW)).toEqual(new Date(2026, 10, 10, 14, 30))
  })
})

describe('labels', () => {
  it('uses relative day names for today and tomorrow', () => {
    expect(relativeDayLabel(NOW, NOW)).toBe('Today')
    expect(relativeDayLabel(new Date(2026, 10, 11, 9), NOW)).toBe('Tomorrow')
    expect(formatDeparture(new Date(2026, 10, 11, 9), NOW)).toMatch(/^Tomorrow, 9:00/)
  })

  it('describes the time until departure', () => {
    expect(formatFromNow(new Date(2026, 10, 10, 14, 12), NOW)).toBe('now')
    expect(formatFromNow(new Date(2026, 10, 10, 14, 55), NOW)).toBe('in 45 min')
    expect(formatFromNow(new Date(2026, 10, 10, 17, 10), NOW)).toBe('in 3 h')
    expect(formatFromNow(new Date(2026, 10, 13, 14, 10), NOW)).toBe('in 3 days')
  })
})
