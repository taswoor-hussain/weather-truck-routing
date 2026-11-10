import { useCallback, useEffect, useState } from 'react'

const PARAM = 'trip'

function readTripId(): string | null {
  return new URLSearchParams(window.location.search).get(PARAM)
}

/** The active trip id, mirrored in `?trip=<id>` so plans survive reloads and can be shared. */
export function useTripIdParam(): [string | null, (tripId: string | null) => void] {
  const [tripId, setTripIdState] = useState<string | null>(readTripId)

  useEffect(() => {
    const onPopState = () => setTripIdState(readTripId())
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const setTripId = useCallback((next: string | null) => {
    const url = new URL(window.location.href)
    if (next) url.searchParams.set(PARAM, next)
    else url.searchParams.delete(PARAM)
    window.history.pushState(null, '', url)
    setTripIdState(next)
  }, [])

  return [tripId, setTripId]
}
