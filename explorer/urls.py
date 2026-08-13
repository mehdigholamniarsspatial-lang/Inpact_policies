from django.urls import path

from . import views
from . import trend_views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/rasters/", views.raster_catalog, name="raster_catalog"),
    path("api/raster/meta/", views.raster_meta, name="raster_meta"),
    path("api/raster/image/", views.raster_image, name="raster_image"),
    path("api/feedback/", views.submit_feedback, name="submit_feedback"),
    path("api/feedback/download/", views.download_feedback, name="download_feedback"),
    # Trend Analysis (piecewise regression) API — ported from the Streamlit app
    path("api/trend/catalog/", trend_views.trend_catalog, name="trend_catalog"),
    path("api/trend/series/", trend_views.trend_series, name="trend_series"),
    path("api/trend/fit/", trend_views.trend_fit, name="trend_fit"),
]
