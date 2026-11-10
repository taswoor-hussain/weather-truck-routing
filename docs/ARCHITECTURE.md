# Architecture

This document describes the design of the Weather-Aware Truck Routing application:
first the high-level design (HLD), then the low-level design (LLD) of each module.

---

## 1. High-Level Design

### 1.1 Problem

A truck driver enters an origin, a destination, a departure time and a load weight.
The system must:

1. Produce **three route options**.
2. Place **checkpoints every 10 / 25 / 50 miles** along each route and compute the
   truck's **ETA** at each one.
3. Look up the **forecast at that place for that ETA** and classify it with the
   wind / rain / snow thresholds and the load-weight rules.
4. **Recommend** a route: fewest Severe miles → fewest High miles → lowest average
   risk → shortest travel time.
5. Visualise routes, checkpoints, ETAs, risk and summaries on a map, plus a
   **weather-risk heatmap** of the trip corridor with a **0–48 h slider**.

### 1.2 System context

```
                       ┌──────────────────────────────────────────────┐
  Browser              │  Django (REST API)                           │
 ┌───────────────┐     │                                              │      ┌──────────────────┐
 │ React SPA     │────▶│  /api/places      ──▶ Geocoding client ──────┼─────▶│ Photon (OSM)     │
 │  - Trip form  │     │  /api/trips       ──▶ Trip planner           │      └──────────────────┘
 │  - Map        │     │                        ├─ Routing client ────┼─────▶ OSRM
 │  - Heatmap    │◀────│                        ├─ Checkpoint sampler │
 │  - Slider     │     │                        ├─ Weather client ────┼─────▶ Open-Meteo
 └───────────────┘     │                        ├─ Risk engine        │
                       │                        └─ Recommender        │
                       │  /api/trips/:id/heatmap ──▶ Corridor heatmap │
                       │                                              │
                       │  PostgreSQL / SQLite (trip plans)  · Cache   │
                       └──────────────────────────────────────────────┘
```

All third-party providers are free and need **no API keys**, so the hosted demo
has no secrets to manage. Base URLs are configurable to point at self-hosted or
commercial instances.

| Concern   | Provider              | Why                                                              |
|-----------|-----------------------|------------------------------------------------------------------|
| Geocoding | Photon (komoot, OSM)  | Designed for search-as-you-type (Nominatim forbids autocomplete) |
| Routing   | OSRM                  | Fast, returns alternatives, per-step durations for accurate ETAs |
| Weather   | Open-Meteo            | Hourly forecast (16 days), imperial units, multi-location batch  |

### 1.3 Request flow

1. **Place search**: the form calls `GET /api/places?q=` (debounced). The backend
   proxies Photon and normalises results to `{label, lat, lon}`.
2. **Plan trip**: `POST /api/trips` with coordinates, departure, load and interval.
   The planner:
   1. fetches route alternatives from OSRM and tops them up to three with
      via-point detours when OSRM returns fewer;
   2. samples checkpoints along each route and computes ETAs from the per-step
      OSRM durations (capped at truck speed);
   3. fetches hourly weather for all checkpoints in **one batched, de-duplicated,
      cached** pass;
   4. classifies each checkpoint, aggregates per-route mileage by risk level, and
      ranks the routes;
   5. persists the plan and returns it (`201`).
3. **Heatmap**: once routes are shown, the SPA calls
   `GET /api/trips/:id/heatmap`. The backend builds a grid over the route corridor,
   fetches 49 hourly forecasts (departure + 0…48 h) per cell, classifies each with
   the same risk engine and returns a compact grid. The slider then only
   **re-renders client-side** — no network traffic while scrubbing.

Splitting plan and heatmap keeps the critical path (routes + recommendation) fast
and lets the heatmap load progressively.

### 1.4 Key decisions

| Decision | Rationale |
|---|---|
| Server-side planning | Risk & recommendation logic lives in one tested place; the client only renders. |
| Persist trip plans | Plans are reproducible and shareable (`?trip=<id>`), and the heatmap is derived from stored geometry. |
| One deployable (Django serves the built SPA) | Same origin → no CORS in production, a single service to host. |
| Heatmap = risk level, not raw weather | The heatmap answers the driver's question ("where is it dangerous for *my* load?") using the exact same rules as checkpoints. |
| Heatmap rendered as a smoothed raster | A small canvas, upsampled with bilinear interpolation in *risk space*, is cheaper and more faithful than density-based heat layers (which sum overlapping points). |
| Forecast slider anchored at departure | Hour 0 = departure, so the slider also shows where the truck is on each route at that time. |

---

## 2. Domain Rules

### 2.1 Risk levels

| Level     | Score |
|-----------|-------|
| Low       | 0 |
| Moderate  | 1 |
| High      | 2 |
| Severe    | 3 |
| No Travel | 4 |

### 2.2 Weather thresholds

Ranges in the brief share their end points (e.g. rain `0.10–0.25` and
`0.25–0.50`). Each band therefore **includes its lower bound and excludes its upper
bound**, except the No Travel thresholds for rain and snow which are stated as
strictly greater (`> 1.00`, `> 3.0`).

| Condition | Moderate | High | Severe | No Travel |
|---|---|---|---|---|
| Wind (mph)     | ≥ 25 | ≥ 35 | ≥ 45 | ≥ 55 |
| Rain (in/hr)   | ≥ 0.10 | ≥ 0.25 | ≥ 0.50 | > 1.00 |
| Snow (in/hr)   | ≥ 0.5 | ≥ 1.0 | ≥ 2.0 | > 3.0 |

The checkpoint level is the **maximum** of the wind, rain and snow levels after the
load rules are applied.

### 2.3 Load rules (applied to wind)

| Wind | Load | Result |
|---|---|---|
| ≥ 55 mph   | any         | No Travel |
| 45–54 mph  | > 30,000 lb | No Travel |
| 35–44 mph  | > 40,000 lb | Severe |

Rules only ever **raise** a level.

### 2.4 Weather at a checkpoint

Open-Meteo hourly values are timestamped at the *end* of the hour for accumulations
(precipitation over the preceding hour) and instantaneous for wind. For an ETA of
14:20 the engine therefore uses:

* **wind**: the nearest hour (14:00),
* **rain / snow**: the hour bucket that contains the ETA, i.e. the value stamped
  15:00 (covers 14:00–15:00).

Rain rate is `rain + showers` (Open-Meteo reports convective showers separately).
Snow uses `snowfall` in inches per hour.

### 2.5 Mileage attribution and average risk

Each checkpoint represents the stretch of road closest to it: half of the
distance to the previous checkpoint plus half to the next. The per-level mileage
therefore always sums to the route length. The **average risk** is the
distance-weighted mean score over those stretches.

### 2.6 Recommendation

Routes are ranked by this tuple, compared in order:

1. No Travel miles. This is an implicit hard constraint: a route that crosses No Travel
   conditions should never beat one that doesn't.
2. Severe miles.
3. High miles.
4. Average risk score.
5. Travel time.

Distances are compared at 0.1 mi precision and average risk at 0.01, so floating
point noise never decides a ranking. If every route contains No Travel segments,
the best one is still ranked first but the plan carries an advisory not to travel at
that departure time. The response also explains *why* the winner won (the first
criterion on which it beats the runner-up).

### 2.7 Truck ETA

OSRM's car profile is used for geometry and durations; each step's speed is capped
at a configurable truck maximum (default 65 mph), which slows highway stretches
while keeping urban stretches as reported. Hours-of-service breaks are out of scope.

---

## 3. Low-Level Design: Backend

```
backend/
├── config/                 # Django project: settings (env-driven), root urls, wsgi
├── core/                   # Cross-cutting, framework-light building blocks
│   ├── exceptions.py       # Domain/API error hierarchy (code, message, status)
│   ├── api.py              # DRF exception handler → consistent error envelope
│   ├── http.py             # Shared requests.Session with retries + timeouts
│   └── geo.py              # LatLon, haversine, polyline decode, interpolation, simplify
├── integrations/           # One module per external provider, returns domain types
│   ├── geocoding.py        # PhotonClient.search(q) → [Place]
│   ├── routing.py          # OsrmClient.alternatives(o, d) / via(o, v, d) → [RawRoute]
│   └── weather.py          # OpenMeteoClient.hourly(points, start, end) → [HourlySeries]
└── trips/                  # The Django app for the feature
    ├── domain/             # Pure Python, no Django imports, fully unit-tested
    │   ├── risk.py         # RiskLevel, threshold tables, load rules, assess()
    │   ├── checkpoints.py  # sample_checkpoints(route, interval, departure)
    │   └── recommendation.py # summarise_route(), rank_routes(), explain()
    ├── services/           # Orchestration, I/O, persistence
    │   ├── route_options.py # get three distinct routes (OSRM + via-point fallback)
    │   ├── planner.py      # TripPlanner.plan(request) → Trip (persisted)
    │   └── heatmap.py      # build_corridor_grid(), CorridorHeatmapService
    ├── models.py           # Trip → RouteOption → Checkpoint
    ├── serializers.py      # Input validation + output shaping
    ├── views.py / urls.py  # Thin API views
    └── tests/
```

**Layering rule:** `views → services → domain`, with `services → integrations`.
The domain layer has no I/O and no Django imports, so it can be tested
exhaustively and in isolation. Integration clients translate provider payloads into
domain types so that no provider-specific JSON leaks past them.

### 3.1 Data model

```
Trip (uuid pk)
  origin_label, origin_lat, origin_lon
  destination_label, destination_lat, destination_lon
  departure_time (UTC), load_weight_lb, checkpoint_interval_mi
  recommendation_reason, advisory, created_at
  └─< RouteOption
        trip FK, label ("A"/"B"/"C"), summary ("I 30, I 57"), rank, is_recommended
        distance_mi, duration_s, geometry (JSON [[lat, lon], …], simplified)
        no_travel_mi, severe_mi, high_mi, moderate_mi, low_mi, average_risk
        └─< Checkpoint
              route FK, sequence, distance_mi, lat, lon, eta
              wind_mph, rain_in_hr, snow_in_hr
              risk_level, wind_level, rain_level, snow_level, reasons (JSON)
```

### 3.2 API

All responses are JSON. Errors are always
`{"error": {"code": "...", "message": "...", "details": {...}}}`.

| Method | Path | Purpose |
|---|---|---|
| GET  | `/api/health` | Liveness |
| GET  | `/api/places?q=dallas` | Place autocomplete |
| POST | `/api/trips` | Plan a trip (201 + full plan) |
| GET  | `/api/trips/{id}` | Fetch a saved plan |
| GET  | `/api/trips/{id}/heatmap` | Corridor risk grid for 0–48 h |

`POST /api/trips` body:

```json
{
  "origin": {"label": "Dallas, TX", "lat": 32.78, "lon": -96.80},
  "destination": {"label": "Chicago, IL", "lat": 41.88, "lon": -87.63},
  "departure_time": "2026-11-11T08:00:00-06:00",
  "load_weight_lb": 38000,
  "checkpoint_interval_mi": 25
}
```

Validation: distinct endpoints, load 1–150,000 lb, interval ∈ {10, 25, 50},
departure no more than 1 h in the past and no more than 7 days ahead, so the
whole trip stays inside the 16-day forecast horizon.

Heatmap response (compact on purpose: about 100 KB for a long trip):

```json
{
  "bounds": {"south": 30.1, "west": -99.2, "north": 43.4, "east": -85.0},
  "rows": 24, "cols": 20,
  "start_time": "2026-11-11T14:00:00Z",
  "hours": 49,
  "cells": [{"row": 3, "col": 7, "risk": [0, 0, 1, 2, …49 values]}]
}
```

### 3.3 External calls & resilience

* One shared `requests.Session` with connection pooling, timeouts and
  `Retry(429, 5xx, backoff)`.
* Weather points are rounded to a 0.05° grid and de-duplicated across routes,
  then fetched in batches of 50 locations, concurrently, and cached per location
  and time window (Django cache, 30 min TTL).
* Provider failures map to `502 upstream_unavailable`; no route found maps to
  `422 no_route`.

---

## 4. Low-Level Design: Frontend

React 18 + TypeScript + Vite, TanStack Query for server state, Leaflet
(react-leaflet) for the map, Tailwind CSS for styling.

```
frontend/src/
├── api/            # client.ts (axios instance + error normaliser), places.ts, trips.ts
├── types/          # API contracts (mirrors serializers)
├── hooks/          # useDebouncedValue, usePlaceSearch, usePlanTrip, useTrip,
│                   # useTripHeatmap, useTripIdParam, usePlayback
├── lib/            # risk.ts (levels, colours), format.ts, heatmapRaster.ts,
│                   # routeProgress.ts (truck position at time t)
├── components/
│   ├── ui/         # Button, Field, Spinner, ErrorAlert, RiskBadge
│   ├── planner/    # TripForm, PlaceAutocomplete
│   ├── routes/     # RouteList, RouteCard, RiskBreakdownBar, CheckpointTable
│   ├── map/        # TripMap, RouteLayer, CheckpointLayer, HeatmapLayer, TruckMarkers
│   └── timeline/   # ForecastSlider
├── pages/          # PlannerPage (composition + page-level state)
└── main.tsx / App.tsx
```

**State:**

* *Server state* (places, trip, heatmap) lives in TanStack Query: caching, retries,
  loading and error states without hand-rolled reducers.
* *UI state* (selected route, forecast hour, heatmap visibility) is local to
  `PlannerPage` and passed down. Nothing else needs to be global.
* The active trip id is mirrored in the URL (`?trip=<uuid>`) so plans survive
  reloads and can be shared.

**Map performance:**

* Leaflet's canvas renderer (`preferCanvas`) for hundreds of checkpoint markers.
* Route geometry is simplified server-side (Ramer–Douglas–Peucker), so payloads stay small.
* The heatmap is one `ImageOverlay`. Scrubbing the slider re-rasterises a canvas
  of a few thousand pixels (well under 1 ms) and swaps its data URL. React state
  updates are batched per animation frame.
* The grid's rows are spaced evenly in Web-Mercator Y, so the image aligns exactly
  with the map projection.
