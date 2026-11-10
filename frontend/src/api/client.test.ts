import { AxiosError, AxiosHeaders, type AxiosResponse } from 'axios'
import { describe, expect, it } from 'vitest'

import { ApiError, toApiError } from './client'

function axiosError(status: number | null, data?: unknown, code?: string): AxiosError {
  const response = status
    ? ({ status, data, headers: {}, config: { headers: new AxiosHeaders() }, statusText: '' } as AxiosResponse)
    : undefined
  return new AxiosError('failed', code, undefined, undefined, response)
}

describe('toApiError', () => {
  it('reads the backend error envelope', () => {
    const error = toApiError(
      axiosError(400, {
        error: {
          code: 'invalid_request',
          message: 'Some fields are invalid.',
          details: { load_weight_lb: ['Too heavy.'], origin: { lat: ['Invalid.'] } },
        },
      }),
    )
    expect(error).toBeInstanceOf(ApiError)
    expect(error.code).toBe('invalid_request')
    expect(error.status).toBe(400)
    expect(error.fieldErrors).toEqual({ load_weight_lb: 'Too heavy.', origin: 'Invalid.' })
  })

  it('reports network failures and timeouts distinctly', () => {
    expect(toApiError(axiosError(null)).code).toBe('network_error')
    expect(toApiError(axiosError(null, undefined, 'ECONNABORTED')).code).toBe('timeout')
  })

  it('falls back to a generic message for unexpected payloads', () => {
    const error = toApiError(axiosError(500, '<html>'))
    expect(error.code).toBe('http_error')
    expect(error.status).toBe(500)
  })

  it('wraps non-HTTP errors', () => {
    expect(toApiError(new Error('boom')).code).toBe('unknown')
  })
})
