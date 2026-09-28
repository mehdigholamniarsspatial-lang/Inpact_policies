from django.urls import path

from . import views

app_name = "policies"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("timeline/", views.timeline, name="timeline"),
    path("categories/", views.categories, name="categories"),
    path("instruments/", views.instruments, name="instruments"),
    path("about/", views.about, name="about"),
    path("policies/", views.explorer, name="explorer"),
    path("policies/<slug:slug>/", views.policy_detail, name="detail"),
    path("oecd-scores/", views.capmf, name="capmf"),
    path("method/", views.method, name="method"),
    path("api/series/", views.api_series, name="api_series"),
    path("api/capmf/", views.api_capmf, name="api_capmf"),
    path("api/selection/", views.api_selection, name="api_selection"),
    path("api/year/<int:year>/", views.api_year_snapshot, name="api_year"),
    path("download/dataset/", views.export_csv, name="export_csv"),
]
