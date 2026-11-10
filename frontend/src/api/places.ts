import type { Place } from '../types/api'
import { apiClient } from './client'

export async function searchPlaces(query: string, signal?: AbortSignal): Promise<Place[]> {
  const { data } = await apiClient.get<Place[]>('/places', { params: { q: query }, signal })
  return data
}
