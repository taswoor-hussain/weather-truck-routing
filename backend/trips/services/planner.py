"""Trip planning use case: routes → checkpoints → weather → risk → ranking → persist."""

from __future__ import annotations

import string
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction

from core.geo import LatLon, simplify
from integrations.routing import RoutingClient, get_router
from integrations.weather import OpenMeteoClient, get_weather_client
from trips.domain.checkpoints import (
    CheckpointSample,
    RoutePath,
    build_route_path,
    sample_checkpoints,
)
from trips.domain.recommendation import RouteRiskSummary, advisory, explain, rank, summarise_route
from trips.domain.risk import RiskAssessment, RiskLevel, assess
from trips.domain.weather import conditions_at
from trips.models import Checkpoint, RouteOption, Trip
from trips.services.route_options import RouteOptionsService

GEOMETRY_TOLERANCE_DEG = 0.0008  # ~80 m: invisible at route-overview zoom levels


@dataclass(frozen=True, slots=True)
class Location:
    label: str
    point: LatLon


@dataclass(frozen=True, slots=True)
class TripRequest:
    origin: Location
    destination: Location
    departure_time: datetime
    load_weight_lb: int
    checkpoint_interval_mi: int


@dataclass(slots=True)
class _AnalysedRoute:
    label: str
    summary_text: str
    path: RoutePath
    samples: list[CheckpointSample]
    assessments: list[RiskAssessment]
    risk: RouteRiskSummary | None = None


class TripPlanner:
    def __init__(
        self,
        router: RoutingClient | None = None,
        weather: OpenMeteoClient | None = None,
        *,
        route_count: int | None = None,
        max_speed_mph: float | None = None,
    ):
        planning = settings.PLANNING
        self.routes = RouteOptionsService(router or get_router())
        self.weather = weather or get_weather_client()
        self.route_count = route_count or planning["ROUTE_OPTIONS"]
        self.max_speed_mph = max_speed_mph or planning["TRUCK_MAX_SPEED_MPH"]
        self.tare_weight_lb = planning["TRUCK_TARE_WEIGHT_LB"]

    def plan(self, request: TripRequest) -> Trip:
        raw_routes = self.routes.fetch(
            request.origin.point,
            request.destination.point,
            self.route_count,
            gross_weight_lb=self.tare_weight_lb + request.load_weight_lb,
        )
        analysed = []
        for label, raw in zip(string.ascii_uppercase, raw_routes, strict=False):
            path = build_route_path(raw.steps, self.max_speed_mph)
            samples = sample_checkpoints(
                path, request.checkpoint_interval_mi, request.departure_time
            )
            analysed.append(_AnalysedRoute(label, raw.summary, path, samples, []))

        self._assess_weather(analysed, request)
        for route in analysed:
            route.risk = summarise_route(
                [s.distance_mi for s in route.samples],
                [a.level for a in route.assessments],
                route.path.distance_mi,
                route.path.duration_s,
            )
        order = rank([route.risk for route in analysed])
        return self._persist(request, analysed, order)

    def _assess_weather(self, routes: list[_AnalysedRoute], request: TripRequest) -> None:
        """One batched forecast lookup for every checkpoint of every route."""
        samples = [sample for route in routes for sample in route.samples]
        latest_eta = max(sample.eta for sample in samples)
        # +1 h: rain/snow for an ETA come from the end of its hour bucket.
        series = self.weather.hourly(
            [s.position for s in samples], request.departure_time, latest_eta + timedelta(hours=1)
        )
        forecasts = iter(series)
        for route in routes:
            route.assessments = [
                assess(conditions_at(next(forecasts), sample.eta), request.load_weight_lb)
                for sample in route.samples
            ]

    @transaction.atomic
    def _persist(
        self, request: TripRequest, routes: list[_AnalysedRoute], order: list[int]
    ) -> Trip:
        best = routes[order[0]]
        runner_up = routes[order[1]] if len(order) > 1 else None
        trip = Trip.objects.create(
            origin_label=request.origin.label,
            origin_lat=request.origin.point.lat,
            origin_lon=request.origin.point.lon,
            destination_label=request.destination.label,
            destination_lat=request.destination.point.lat,
            destination_lon=request.destination.point.lon,
            departure_time=request.departure_time,
            load_weight_lb=request.load_weight_lb,
            checkpoint_interval_mi=request.checkpoint_interval_mi,
            recommendation_reason=explain(
                best.risk,
                runner_up.risk if runner_up else None,
                f"Route {runner_up.label}" if runner_up else "",
            ),
            advisory=advisory(best.risk),
        )

        rank_of = {route_index: position for position, route_index in enumerate(order)}
        options = RouteOption.objects.bulk_create(
            [self._route_option(trip, route, rank_of[i]) for i, route in enumerate(routes)]
        )
        Checkpoint.objects.bulk_create(
            [
                self._checkpoint(option, sample, assessment)
                for option, route in zip(options, routes, strict=True)
                for sample, assessment in zip(route.samples, route.assessments, strict=True)
            ]
        )
        return trip

    @staticmethod
    def _route_option(trip: Trip, route: _AnalysedRoute, rank_position: int) -> RouteOption:
        risk = route.risk
        return RouteOption(
            trip=trip,
            label=route.label,
            summary=route.summary_text[:255],
            rank=rank_position,
            is_recommended=rank_position == 0,
            distance_mi=route.path.distance_mi,
            duration_s=route.path.duration_s,
            geometry=[p.as_list() for p in simplify(route.path.points, GEOMETRY_TOLERANCE_DEG)],
            no_travel_mi=risk.miles(RiskLevel.NO_TRAVEL),
            severe_mi=risk.miles(RiskLevel.SEVERE),
            high_mi=risk.miles(RiskLevel.HIGH),
            moderate_mi=risk.miles(RiskLevel.MODERATE),
            low_mi=risk.miles(RiskLevel.LOW),
            average_risk=risk.average_risk,
        )

    @staticmethod
    def _checkpoint(
        option: RouteOption, sample: CheckpointSample, assessment: RiskAssessment
    ) -> Checkpoint:
        return Checkpoint(
            route=option,
            sequence=sample.sequence,
            distance_mi=sample.distance_mi,
            lat=sample.position.lat,
            lon=sample.position.lon,
            eta=sample.eta,
            wind_mph=assessment.conditions.wind_mph,
            rain_in_hr=assessment.conditions.rain_in_hr,
            snow_in_hr=assessment.conditions.snow_in_hr,
            risk_level=assessment.level,
            wind_level=assessment.wind_level,
            rain_level=assessment.rain_level,
            snow_level=assessment.snow_level,
            reasons=list(assessment.reasons),
        )
