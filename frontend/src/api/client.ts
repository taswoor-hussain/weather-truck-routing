import axios, { type AxiosError } from 'axios'

import type { ApiErrorBody } from '../types/api'

/** Normalised error for every failed API call, whatever went wrong. */
export class ApiError extends Error {
  readonly code: string
  readonly status: number | null
  readonly details: Record<string, unknown>

  constructor(message: string, code: string, status: number | null, details: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }

  /** First validation message per field, e.g. `{ load_weight_lb: 'Ensure this value…' }`. */
  get fieldErrors(): Record<string, string> {
    const result: Record<string, string> = {}
    for (const [field, value] of Object.entries(this.details)) {
      const message = Array.isArray(value) ? value[0] : value
      if (typeof message === 'string') result[field] = message
      else if (message && typeof message === 'object') result[field] = Object.values(message).flat().join(' ')
    }
    return result
  }
}

function isApiErrorBody(data: unknown): data is ApiErrorBody {
  return typeof data === 'object' && data !== null && 'error' in data
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (axios.isAxiosError(error)) {
    const { response, code } = error as AxiosError
    if (response && isApiErrorBody(response.data)) {
      const body = response.data.error
      return new ApiError(body.message, body.code, response.status, body.details)
    }
    if (code === 'ECONNABORTED') {
      return new ApiError('The request took too long. Please try again.', 'timeout', null)
    }
    if (!response) {
      return new ApiError('Cannot reach the server. Check your connection.', 'network_error', null)
    }
    return new ApiError('Something went wrong. Please try again.', 'http_error', response.status)
  }
  return new ApiError('Something went wrong. Please try again.', 'unknown', null)
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  // Planning a long trip calls several upstream providers.
  timeout: 90_000,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => Promise.reject(toApiError(error)),
)
