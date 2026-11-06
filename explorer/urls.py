from django.urls import path

from . import views
from . import trend_views

urlpatterns = [
    path("", views.index, name="index"),
    # Spatial Environmental Mapping opened on its own ("Open in new window")
    path("map/", views.map_page, name="map_page"),
    path("api/rasters/", views.raster_catalog, name="raster_catalog"),
    path("api/raster/meta/", views.raster_meta, name="raster_meta"),
    path("api/raster/image/", views.raster_image, name="raster_image"),
    path("api/edgar/", views.edgar_catalog, name="edgar_catalog"),
    path("api/edgar/layer/", views.edgar_layer, name="edgar_layer"),
    path("api/inverse/", views.inverse_catalog, name="inverse_catalog"),
    path("api/inverse/layer/", views.inverse_layer, name="inverse_layer"),
    # Download of the selected map layer: GeoTIFF data or a JPEG map with legend
    path("api/map/export/<str:fmt>/", views.map_export, name="map_export"),
    # Time series of a pixel, region or the whole grid (map window's Time series panel)
    path("api/map/timeseries/", views.map_timeseries, name="map_timeseries"),
    path("api/map/counties/", views.map_counties, name="map_counties"),
    path("api/feedback/", views.submit_feedback, name="submit_feedback"),
    path("api/feedback/download/", views.download_feedback, name="download_feedback"),
    # Trend Analysis (piecewise regression) API — ported from the Streamlit app
    path("api/trend/catalog/", trend_views.trend_catalog, name="trend_catalog"),
    path("api/trend/series/", trend_views.trend_series, name="trend_series"),
    path("api/trend/fit/", trend_views.trend_fit, name="trend_fit"),
]
