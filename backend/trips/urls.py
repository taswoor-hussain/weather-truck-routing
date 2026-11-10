from django.urls import path

from trips import views

urlpatterns = [
    path("health", views.HealthView.as_view(), name="health"),
    path("places", views.PlaceSearchView.as_view(), name="place-search"),
    path("trips", views.TripListCreateView.as_view(), name="trip-list"),
    path("trips/<uuid:trip_id>", views.TripDetailView.as_view(), name="trip-detail"),
    path("trips/<uuid:trip_id>/heatmap", views.TripHeatmapView.as_view(), name="trip-heatmap"),
]
