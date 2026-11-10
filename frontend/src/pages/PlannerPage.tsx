import type { ApiError } from '../api/client'
import { CheckpointMarkers } from '../components/map/CheckpointMarkers'
import { EndpointMarkers } from '../components/map/EndpointMarkers'
import { FitToTrip } from '../components/map/FitToTrip'
import { HeatmapLayer } from '../components/map/HeatmapLayer'
import { RouteLines } from '../components/map/RouteLines'
import { TripMap } from '../components/map/TripMap'
import { TruckMarkers } from '../components/map/TruckMarkers'
import { TripForm } from '../components/planner/TripForm'
import { RouteComparison } from '../components/routes/RouteComparison'
import { ForecastPanel } from '../components/timeline/ForecastPanel'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Spinner } from '../components/ui/Spinner'
import { usePlanTrip, useTrip, useTripHeatmap } from '../hooks/useTrip'
import { useTripIdParam } from '../hooks/useTripIdParam'
import { useTripViewState } from '../hooks/useTripViewState'
import { addHours } from '../lib/format'
import type { TripRequest } from '../types/api'

const FORECAST_HOURS = 48

export function PlannerPage() {
  const [tripId, setTripId] = useTripIdParam()
  const planTrip = usePlanTrip()
  const tripQuery = useTrip(tripId)
  const trip = tripQuery.data
  const heatmapQuery = useTripHeatmap(trip?.id ?? null)
  const heatmap = heatmapQuery.data
  const view = useTripViewState(trip)
  const { selectedRouteId, selectRoute, forecastHour } = view

  // Hour 0 is the departure hour (the heatmap grid starts at its top of the hour).
  const forecastStart = heatmap?.start_time ?? trip?.departure_time
  const forecastTime = forecastStart ? addHours(forecastStart, forecastHour) : null

  const planError = planTrip.error as ApiError | null

  const handlePlan = (request: TripRequest) => {
    planTrip.mutate(request, { onSuccess: (planned) => setTripId(planned.id) })
  }

  return (
    <div className="flex h-full flex-col lg:flex-row">
      <aside className="flex w-full shrink-0 flex-col border-slate-200 bg-slate-50 lg:h-full lg:w-[420px] lg:border-r">
        <header className="border-b border-slate-200 bg-white px-5 py-4">
          <h1 className="text-lg font-bold tracking-tight text-slate-900">Weather-Aware Truck Routing</h1>
          <p className="text-sm text-slate-500">Compare routes by forecast risk at your truck's arrival time.</p>
        </header>

        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-4">
          <TripForm onSubmit={handlePlan} submitting={planTrip.isPending} serverErrors={planError?.fieldErrors} />

          {planError && !Object.keys(planError.fieldErrors).length && (
            <Alert tone="error" title="Could not plan this trip">
              {planError.message}
            </Alert>
          )}

          {planTrip.isPending ? (
            <div className="flex items-center gap-3 rounded-xl bg-white p-4 text-sm text-slate-600 ring-1 ring-slate-200">
              <Spinner className="size-5 text-blue-700" />
              Finding truck routes and checking forecasts at each checkpoint's ETA…
            </div>
          ) : tripQuery.isLoading ? (
            <div className="flex items-center gap-3 text-sm text-slate-600">
              <Spinner /> Loading saved trip…
            </div>
          ) : tripQuery.isError ? (
            <Alert
              tone="error"
              title="Saved trip unavailable"
              action={
                <Button variant="secondary" onClick={() => setTripId(null)}>
                  Start a new trip
                </Button>
              }
            >
              {(tripQuery.error as ApiError).message}
            </Alert>
          ) : (
            trip && <RouteComparison trip={trip} selectedRouteId={selectedRouteId} onSelectRoute={selectRoute} />
          )}
        </div>
      </aside>

      <main className="relative min-h-[60vh] flex-1">
        <TripMap>
          {trip && (
            <>
              <FitToTrip trip={trip} />
              {heatmap && view.showHeatmap && <HeatmapLayer heatmap={heatmap} hour={forecastHour} />}
              <RouteLines routes={trip.routes} selectedRouteId={selectedRouteId} onSelect={selectRoute} />
              <CheckpointMarkers routes={trip.routes} selectedRouteId={selectedRouteId} />
              <EndpointMarkers origin={trip.origin} destination={trip.destination} />
              {forecastTime && (
                <TruckMarkers routes={trip.routes} time={forecastTime} selectedRouteId={selectedRouteId} />
              )}
            </>
          )}
        </TripMap>

        {trip && forecastStart && (
          <div className="pointer-events-none absolute inset-x-3 bottom-6 z-[1000] mx-auto max-w-2xl">
            <ForecastPanel
              startTime={forecastStart}
              maxHour={heatmap ? heatmap.hours - 1 : FORECAST_HOURS}
              hour={forecastHour}
              onHourChange={view.setForecastHour}
              showHeatmap={view.showHeatmap}
              onShowHeatmapChange={view.setShowHeatmap}
              heatmapStatus={heatmapQuery.status}
              onRetryHeatmap={heatmapQuery.refetch}
            />
          </div>
        )}
      </main>
    </div>
  )
}
