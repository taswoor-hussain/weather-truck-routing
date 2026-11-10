import type { Heatmap, Trip, TripRequest } from '../types/api'
import { apiClient } from './client'

export async function createTrip(request: TripRequest): Promise<Trip> {
  const { data } = await apiClient.post<Trip>('/trips', request)
  return data
}

export async function getTrip(tripId: string, signal?: AbortSignal): Promise<Trip> {
  const { data } = await apiClient.get<Trip>(`/trips/${tripId}`, { signal })
  return data
}

export async function getTripHeatmap(tripId: string, signal?: AbortSignal): Promise<Heatmap> {
  const { data } = await apiClient.get<Heatmap>(`/trips/${tripId}/heatmap`, { signal })
  return data
}
