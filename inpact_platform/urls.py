"""Top-level URL configuration."""
from django.urls import include, path

urlpatterns = [
    # Ireland Climate Policy Timeline (embedded in the Explorer's "Policy Timeline" tab)
    path("policy/", include("policies.urls")),
    path("", include("explorer.urls")),
]
