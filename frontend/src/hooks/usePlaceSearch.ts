import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { searchPlaces } from '../api/places'
import type { Place } from '../types/api'
import { useDebouncedValue } from './useDebouncedValue'

const MIN_QUERY_LENGTH = 2
const DEBOUNCE_MS = 250

export interface PlaceSearch {
  places: Place[]
  /** True while waiting for the debounce or the request: results may be stale. */
  isSearching: boolean
  isError: boolean
}

/** Debounced place autocomplete; superseded requests are cancelled. */
export function usePlaceSearch(query: string): PlaceSearch {
  const trimmed = query.trim()
  const debounced = useDebouncedValue(trimmed, DEBOUNCE_MS)
  const enabled = debounced.length >= MIN_QUERY_LENGTH
  const result = useQuery({
    queryKey: ['places', debounced],
    queryFn: ({ signal }) => searchPlaces(debounced, signal),
    enabled,
    staleTime: 10 * 60_000,
    placeholderData: keepPreviousData,
  })
  return {
    places: enabled ? (result.data ?? []) : [],
    isSearching: trimmed !== debounced || result.isFetching,
    isError: result.isError,
  }
}
