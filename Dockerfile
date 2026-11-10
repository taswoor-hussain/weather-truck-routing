# --- Stage 1: build the React app -------------------------------------------
FROM node:24-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Django API that also serves the built app ---------------------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FRONTEND_DIST_DIR=/app/frontend/dist \
    PORT=8000

WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt
COPY backend/ ./
COPY --from=frontend /frontend/dist /app/frontend/dist
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

RUN useradd --create-home app && chown -R app /app
USER app
EXPOSE 8000

# Threads matter: planning waits on several upstream HTTP calls.
CMD python manage.py migrate --noinput && \
    gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} \
      --worker-class gthread --workers 2 --threads 8 --timeout 120 --access-logfile -
