import { useCallback, useState } from 'react'

import type { Trip } from '../types/api'

interface ViewState {
  tripId: string | null
  routeId: number | null
  forecastHour: number
}

/**
 * UI state that belongs to the trip on screen. It resets when a different trip is
 * shown (React's "adjust state during render" pattern, no effect needed).
 * Callbacks are stable so memoised map layers don't re-render needlessly.
 */
export function useTripViewState(trip: Trip | undefined) {
  const tripId = trip?.id ?? null
  const [state, setState] = useState<ViewState>({ tripId, routeId: null, forecastHour: 0 })
  const [showHeatmap, setShowHeatmap] = useState(true)

  if (state.tripId !== tripId) {
    setState({ tripId, routeId: null, forecastHour: 0 })
  }

  const selectRoute = useCallback((routeId: number) => setState((s) => ({ ...s, routeId })), [])
  const setForecastHour = useCallback((forecastHour: number) => setState((s) => ({ ...s, forecastHour })), [])

  return {
    selectedRouteId: state.routeId ?? trip?.recommendation.route_id ?? trip?.routes[0]?.id ?? null,
    selectRoute,
    forecastHour: state.forecastHour,
    setForecastHour,
    showHeatmap,
    setShowHeatmap,
  }
}
