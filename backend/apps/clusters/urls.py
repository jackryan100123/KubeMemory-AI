"""URL routing for clusters API. Prefix: api/ (from main urls)."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ClusterConnectionViewSet

router = DefaultRouter()
router.register(r"clusters", ClusterConnectionViewSet, basename="cluster")

urlpatterns = [
    path("", include(router.urls)),
]
