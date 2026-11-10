import { useId, useState, type KeyboardEvent } from 'react'

import { usePlaceSearch } from '../../hooks/usePlaceSearch'
import type { Place } from '../../types/api'
import { Field } from '../ui/Field'
import { describedBy, inputClass } from '../ui/fieldStyles'
import { Spinner } from '../ui/Spinner'

interface PlaceAutocompleteProps {
  label: string
  placeholder: string
  value: Place | null
  onChange: (place: Place | null) => void
  error?: string
}

/** Accessible combobox backed by the place search API. */
export function PlaceAutocomplete({ label, placeholder, value, onChange, error }: PlaceAutocompleteProps) {
  const id = useId()
  const listId = `${id}-options`
  const [text, setText] = useState(value?.label ?? '')
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const search = usePlaceSearch(open ? text : '')
  const options = open ? (search.data ?? []) : []

  // Keep the text in sync when the selected place changes from outside (e.g. form reset).
  const [syncedValue, setSyncedValue] = useState(value)
  if (value !== syncedValue) {
    setSyncedValue(value)
    setText(value?.label ?? '')
  }

  const select = (place: Place) => {
    onChange(place)
    setText(place.label)
    setOpen(false)
  }

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown' && options.length) {
      event.preventDefault()
      setOpen(true)
      setActiveIndex((i) => (i + 1) % options.length)
    } else if (event.key === 'ArrowUp' && options.length) {
      event.preventDefault()
      setActiveIndex((i) => (i - 1 + options.length) % options.length)
    } else if (event.key === 'Enter' && open && options[activeIndex]) {
      event.preventDefault()
      select(options[activeIndex])
    } else if (event.key === 'Escape') {
      setOpen(false)
    }
  }

  const showList = open && text.trim().length >= 2

  return (
    <Field id={id} label={label} error={error}>
      <div className="relative">
        <input
          id={id}
          type="text"
          role="combobox"
          autoComplete="off"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={showList && options[activeIndex] ? `${listId}-${activeIndex}` : undefined}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy(id, error)}
          className={`${inputClass} pr-9`}
          placeholder={placeholder}
          value={text}
          onChange={(event) => {
            setText(event.target.value)
            setOpen(true)
            setActiveIndex(0)
            if (value) onChange(null)
          }}
          onFocus={() => {
            if (text && !value) setOpen(true)
          }}
          onBlur={() => setOpen(false)}
          onKeyDown={onKeyDown}
        />
        {search.isFetching && open && (
          <Spinner className="absolute top-2.5 right-3 size-4 text-slate-400" />
        )}
        {showList && (
          <ul
            id={listId}
            role="listbox"
            className="absolute z-[1000] mt-1 max-h-64 w-full overflow-auto rounded-lg bg-white py-1 text-sm shadow-lg ring-1 ring-slate-200"
          >
            {options.map((place, index) => (
              <li
                key={`${place.label}-${place.lat}-${place.lon}`}
                id={`${listId}-${index}`}
                role="option"
                aria-selected={index === activeIndex}
                className={`cursor-pointer px-3 py-2 ${index === activeIndex ? 'bg-blue-50 text-blue-900' : 'text-slate-700'}`}
                // Select on mousedown so the input's blur doesn't close the list first.
                onMouseDown={(event) => {
                  event.preventDefault()
                  select(place)
                }}
                onMouseEnter={() => setActiveIndex(index)}
              >
                {place.label}
              </li>
            ))}
            {!search.isFetching && options.length === 0 && (
              <li className="px-3 py-2 text-slate-500">
                {search.isError ? 'Search is unavailable right now.' : 'No matching places.'}
              </li>
            )}
          </ul>
        )}
      </div>
    </Field>
  )
}
