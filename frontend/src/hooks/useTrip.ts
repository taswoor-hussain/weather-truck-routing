import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createTrip, getTrip, getTripHeatmap } from '../api/trips'
import type { Trip } from '../types/api'

export const tripKeys = {
  detail: (tripId: string) => ['trips', tripId] as const,
  heatmap: (tripId: string) => ['trips', tripId, 'heatmap'] as const,
}

/** Plan a new trip; the result is seeded into the cache so it renders immediately. */
export function usePlanTrip() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createTrip,
    onSuccess: (trip: Trip) => queryClient.setQueryData(tripKeys.detail(trip.id), trip),
  })
}

/** A saved trip plan. Plans are immutable, so they never go stale. */
export function useTrip(tripId: string | null) {
  return useQuery({
    queryKey: tripKeys.detail(tripId ?? ''),
    queryFn: ({ signal }) => getTrip(tripId!, signal),
    enabled: Boolean(tripId),
    staleTime: Infinity,
    retry: (count, error) => count < 2 && !('status' in error && error.status === 404),
  })
}

/** Corridor heatmap, loaded after the plan so routes appear first. */
export function useTripHeatmap(tripId: string | null) {
  return useQuery({
    queryKey: tripKeys.heatmap(tripId ?? ''),
    queryFn: ({ signal }) => getTripHeatmap(tripId!, signal),
    enabled: Boolean(tripId),
    staleTime: 15 * 60_000,
  })
}
