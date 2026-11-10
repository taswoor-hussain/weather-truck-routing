import { useEffect, useState } from 'react'

/**
 * Auto-advance an hour value one step at a time until `max`.
 * Returns `[playing, setPlaying]`; playback stops by itself at `max`.
 */
export function usePlayback(
  value: number,
  max: number,
  onChange: (next: number) => void,
  stepMs = 700,
): [boolean, (playing: boolean) => void] {
  const [requested, setRequested] = useState(false)
  const playing = requested && value < max

  useEffect(() => {
    if (!playing) return
    const timer = window.setTimeout(() => onChange(value + 1), stepMs)
    return () => window.clearTimeout(timer)
  }, [playing, value, onChange, stepMs])

  return [playing, setRequested]
}
