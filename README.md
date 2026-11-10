# Weather-Aware Truck Routing

A React + Django application that helps a truck driver choose the **safest route**
by combining truck routing, **time-aware** weather forecasts along each route, and
**load-dependent** risk rules.

Enter an origin, destination, departure time and load weight. The app then:

1. Builds **3 truck routes** (Valhalla `truck` costing with the truck's gross weight).
2. Places **checkpoints every 10 / 25 / 50 miles** and computes the truck's **ETA** at each one.
3. Reads the **forecast at each checkpoint for that ETA** (Open-Meteo) and classifies
   wind, rain and snow with the risk and load rules.
4. **Recommends** a route: fewest No Travel → Severe → High miles → lowest average
   risk → shortest drive time, and explains why it won.
5. Shows routes, checkpoints (risk, ETA, readings), route summaries, a **corridor
   risk heatmap** and a **0–48 h forecast slider** (with each truck's position at that hour).


## Tech stack

| Layer    | Choice |
|----------|--------|
| Frontend | React 19, TypeScript (strict), Vite, TanStack Query, axios, Leaflet / react-leaflet, Tailwind CSS |
| Backend  | Django 5.2, Django REST Framework, django-environ, WhiteNoise, gunicorn |
| Data     | SQLite (default) or PostgreSQL via `DATABASE_URL` |
| Providers (no API keys) | [Valhalla](https://valhalla1.openstreetmap.de) (truck routing), [Open-Meteo](https://open-meteo.com) (hourly forecast), [Photon](https://photon.komoot.io) (geocoding), Esri canvas basemap |
| Quality  | pytest (124 tests), Vitest, ruff, oxlint, GitHub Actions CI |

## Run locally

Requirements: Python 3.10+ and Node 20+.

```bash
# Backend (http://127.0.0.1:8000)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver

# Frontend (http://localhost:5173, proxies /api to Django)
cd frontend
npm install
npm run dev
```

Or run everything as the production image:

```bash
docker build -t weather-truck-routing .
docker run -p 8000:8000 -e DJANGO_SECRET_KEY=change-me -e DJANGO_SECURE_SSL_REDIRECT=false weather-truck-routing
# open http://localhost:8000
```

### Tests and checks

```bash
cd backend && pytest && ruff check .
cd frontend && npm test && npm run lint && npm run build
```

## Deploy

The Docker image serves both the API and the built SPA, so it runs as a single service.
On **Render**: *New → Blueprint* and pick this repo (`render.yaml`). Any Docker host
works the same way: set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` and
`DJANGO_CSRF_TRUSTED_ORIGINS`, and optionally `DATABASE_URL`. See `backend/.env.example`.

## How the logic works

The full rationale is in **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** (HLD + LLD). In short:

- **Thresholds** (lower bound inclusive; rain/snow No Travel strictly greater):

  | | Moderate | High | Severe | No Travel |
  |---|---|---|---|---|
  | Wind mph | ≥25 | ≥35 | ≥45 | ≥55 |
  | Rain in/hr | ≥0.10 | ≥0.25 | ≥0.50 | >1.00 |
  | Snow in/hr | ≥0.5 | ≥1.0 | ≥2.0 | >3.0 |

- **Load rules** raise the wind level: 45–54 mph with more than 30,000 lb → No Travel;
  35–44 mph with more than 40,000 lb → Severe. A checkpoint's level is the worst of
  its wind, rain and snow levels.
- **Weather at ETA**: wind comes from the nearest hour. Rain (`rain + showers`) and
  snow come from the hour bucket that contains the ETA.
- **Miles per risk level**: each checkpoint covers the road half-way to its
  neighbours, so the mileage per level adds up to the route length. Average risk is
  distance-weighted.
- **Recommendation**: ranked lexicographically as above. Distances are compared at
  0.1 mi so floating-point noise never decides. An advisory appears when even the best
  route crosses Severe or No Travel conditions.
- **Heatmap**: a Mercator-aligned grid covering only the route corridor, with 49
  hourly risk levels per cell computed by the same engine and load. The browser
  interpolates it bilinearly *in risk space* into one image overlay. Frames are cached
  per hour, so the slider never waits on the network.

## Project structure

```
backend/
  config/         settings (env-driven), urls, SPA fallback
  core/           error envelope, resilient HTTP client, geo utilities
  integrations/   routing/ (Valhalla, OSRM), weather (Open-Meteo), geocoding (Photon)
  trips/
    domain/       pure logic: risk rules, checkpoints & ETAs, weather sampling,
                  recommendation, corridor grid  (no Django, fully unit-tested)
    services/     planner, route options, heatmap (orchestration + persistence)
    models / serializers / views / urls / tests
frontend/src/
  api/            axios client + error normaliser, endpoint functions
  hooks/          query hooks, URL state, debounce, playback, per-trip view state
  lib/            risk palette, formatting, heatmap rasteriser, truck position
  components/     ui/, planner/, routes/, map/, timeline/
  pages/          PlannerPage
docs/ARCHITECTURE.md
```

## Assumptions and limitations

- Gross weight for routing = 35,000 lb tare + load (`TRUCK_TARE_WEIGHT_LB`).
- Sustained 10 m wind is used for wind risk (gusts are not part of the rules).
- Departures must be within 7 days so the whole trip stays inside the forecast horizon.
- Hours-of-service breaks are not modelled in ETAs.
- The free public providers have rate limits. Weather lookups are de-duplicated on a
  0.05° grid and cached for 30 min, and the API is throttled. Base URLs are
  configurable for self-hosted or commercial instances.
