from django.contrib import admin
from django.urls import include, path, re_path

from config.spa import spa_index

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("trips.urls")),
    # Everything else is the single-page app.
    re_path(r"^(?!api/|admin/|static/).*$", spa_index, name="spa"),
]
