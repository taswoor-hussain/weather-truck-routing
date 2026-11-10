from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.geocoding import get_geocoder
from trips.selectors import get_trip
from trips.serializers import PlaceQuerySerializer, TripRequestSerializer, TripSerializer
from trips.services.planner import TripPlanner


class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class PlaceSearchView(APIView):
    throttle_scope = "places"

    def get(self, request):
        query = PlaceQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        places = get_geocoder().search(query.validated_data["q"])
        return Response([{"label": p.label, "lat": p.lat, "lon": p.lon} for p in places])


class TripListCreateView(APIView):
    throttle_scope = "plan"

    def post(self, request):
        serializer = TripRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip = TripPlanner().plan(serializer.to_request())
        return Response(TripSerializer(get_trip(trip.pk)).data, status=status.HTTP_201_CREATED)


class TripDetailView(APIView):
    def get(self, request, trip_id):
        return Response(TripSerializer(get_trip(trip_id)).data)
