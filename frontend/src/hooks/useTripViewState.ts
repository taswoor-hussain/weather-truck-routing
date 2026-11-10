import { useState } from 'react'

import type { Trip } from '../types/api'

interface ViewState {
  tripId: string | null
  routeId: number | null
}

/**
 * UI state that belongs to the trip on screen: it resets when a different trip is
 * shown (React's "adjust state during render" pattern, no effect needed).
 */
export function useTripViewState(trip: Trip | undefined) {
  const tripId = trip?.id ?? null
  const [state, setState] = useState<ViewState>({ tripId, routeId: null })

  if (state.tripId !== tripId) {
    setState({ tripId, routeId: null })
  }

  const selectedRouteId = state.routeId ?? trip?.recommendation.route_id ?? trip?.routes[0]?.id ?? null

  return {
    selectedRouteId,
    selectRoute: (routeId: number) => setState((s) => ({ ...s, routeId })),
  }
}
