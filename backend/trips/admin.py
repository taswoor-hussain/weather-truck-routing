from django.contrib import admin

from trips.models import Checkpoint, RouteOption, Trip


class RouteOptionInline(admin.TabularInline):
    model = RouteOption
    extra = 0
    fields = ("label", "rank", "is_recommended", "summary", "distance_mi", "severe_mi", "high_mi")
    readonly_fields = fields
    show_change_link = True


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("origin_label", "destination_label", "departure_time", "load_weight_lb")
    search_fields = ("origin_label", "destination_label")
    inlines = [RouteOptionInline]


class CheckpointInline(admin.TabularInline):
    model = Checkpoint
    extra = 0
    fields = (
        "sequence",
        "distance_mi",
        "eta",
        "wind_mph",
        "rain_in_hr",
        "snow_in_hr",
        "risk_level",
    )
    readonly_fields = fields


@admin.register(RouteOption)
class RouteOptionAdmin(admin.ModelAdmin):
    list_display = ("trip", "label", "rank", "is_recommended", "distance_mi")
    exclude = ("geometry",)
    inlines = [CheckpointInline]
