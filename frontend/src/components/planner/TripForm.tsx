import { useState, type FormEvent } from 'react'

import { useNow } from '../../hooks/useNow'
import { formatFromNow, isDepartureAllowed, MAX_DAYS_AHEAD } from '../../lib/departure'
import { nextFullHour } from '../../lib/format'
import type { CheckpointInterval, Place, TripRequest } from '../../types/api'
import { Button } from '../ui/Button'
import { Field } from '../ui/Field'
import { describedBy, inputClass } from '../ui/fieldStyles'
import { DeparturePicker } from './DeparturePicker'
import { PlaceAutocomplete } from './PlaceAutocomplete'

const INTERVALS: CheckpointInterval[] = [10, 25, 50]
const MAX_LOAD_LB = 150_000

type FieldErrors = Partial<Record<keyof TripRequest, string>>

interface TripFormProps {
  onSubmit: (request: TripRequest) => void
  submitting: boolean
  /** Field errors returned by the API. */
  serverErrors?: Record<string, string>
}

function validate(values: {
  origin: Place | null
  destination: Place | null
  departure: Date
  load: string
}): FieldErrors {
  const errors: FieldErrors = {}
  if (!values.origin) errors.origin = 'Choose an origin from the suggestions.'
  if (!values.destination) errors.destination = 'Choose a destination from the suggestions.'
  if (values.origin && values.destination && values.origin.label === values.destination.label) {
    errors.destination = 'Destination must differ from the origin.'
  }
  if (!isDepartureAllowed(values.departure, new Date())) {
    errors.departure_time = `Choose a time from now to ${MAX_DAYS_AHEAD} days ahead (forecast range).`
  }
  const load = Number(values.load)
  if (!Number.isInteger(load) || load < 1 || load > MAX_LOAD_LB) {
    errors.load_weight_lb = `Enter a whole number of pounds between 1 and ${MAX_LOAD_LB.toLocaleString()}.`
  }
  return errors
}

export function TripForm({ onSubmit, submitting, serverErrors = {} }: TripFormProps) {
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [departure, setDeparture] = useState(nextFullHour)
  const [load, setLoad] = useState('38000')
  const [interval, setCheckpointInterval] = useState<CheckpointInterval>(25)
  const [errors, setErrors] = useState<FieldErrors>({})
  const now = useNow()

  const errorFor = (field: keyof TripRequest) => errors[field] ?? serverErrors[field]

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const nextErrors = validate({ origin, destination, departure, load })
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length || !origin || !destination) return
    onSubmit({
      origin,
      destination,
      departure_time: departure.toISOString(),
      load_weight_lb: Number(load),
      checkpoint_interval_mi: interval,
    })
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-3.5">
      <PlaceAutocomplete
        label="Origin"
        placeholder="e.g. Dallas, TX"
        value={origin}
        onChange={setOrigin}
        error={errorFor('origin')}
      />
      <PlaceAutocomplete
        label="Destination"
        placeholder="e.g. Chicago, IL"
        value={destination}
        onChange={setDestination}
        error={errorFor('destination')}
      />

      <div className="grid grid-cols-2 gap-3">
        <Field
          id="departure"
          label="Departure"
          error={errorFor('departure_time')}
          hint={`Departs ${formatFromNow(departure, now)}`}
        >
          <DeparturePicker
            id="departure"
            value={departure}
            onChange={setDeparture}
            invalid={Boolean(errorFor('departure_time'))}
            describedBy={describedBy('departure', errorFor('departure_time'), 'hint')}
          />
        </Field>
        <Field id="load" label="Load weight (lb)" error={errorFor('load_weight_lb')}>
          <input
            id="load"
            type="number"
            inputMode="numeric"
            min={1}
            max={MAX_LOAD_LB}
            step={500}
            className={inputClass}
            value={load}
            onChange={(event) => setLoad(event.target.value)}
            aria-invalid={Boolean(errorFor('load_weight_lb'))}
            aria-describedby={describedBy('load', errorFor('load_weight_lb'))}
          />
        </Field>
      </div>

      <fieldset>
        <legend className="mb-1 block text-xs font-semibold tracking-wide text-slate-600 uppercase">
          Weather checkpoint every
        </legend>
        <div className="grid grid-cols-3 rounded-lg bg-slate-100 p-1 ring-1 ring-slate-200">
          {INTERVALS.map((miles) => (
            <label
              key={miles}
              className={`cursor-pointer rounded-md py-1.5 text-center text-sm font-medium transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-blue-700 ${
                interval === miles ? 'bg-white text-blue-800 shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <input
                type="radio"
                name="interval"
                value={miles}
                checked={interval === miles}
                onChange={() => setCheckpointInterval(miles)}
                className="sr-only"
              />
              {miles} mi
            </label>
          ))}
        </div>
      </fieldset>

      <Button type="submit" loading={submitting} className="w-full">
        {submitting ? 'Planning routes…' : 'Find safest route'}
      </Button>
    </form>
  )
}
