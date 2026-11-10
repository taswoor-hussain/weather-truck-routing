import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { searchPlaces } from '../api/places'
import { useDebouncedValue } from './useDebouncedValue'

const MIN_QUERY_LENGTH = 2
const DEBOUNCE_MS = 250

/** Debounced place autocomplete; requests are cancelled when the query changes. */
export function usePlaceSearch(query: string) {
  const debounced = useDebouncedValue(query.trim(), DEBOUNCE_MS)
  const enabled = debounced.length >= MIN_QUERY_LENGTH
  return useQuery({
    queryKey: ['places', debounced],
    queryFn: ({ signal }) => searchPlaces(debounced, signal),
    enabled,
    staleTime: 10 * 60_000,
    placeholderData: keepPreviousData,
  })
}
