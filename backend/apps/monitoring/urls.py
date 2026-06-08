"""URL routing for monitoring app."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .notification_views import NotificationConfigViewSet
from .views import TaskLogListView

router = DefaultRouter()
router.register(r"notifications/configs", NotificationConfigViewSet, basename="notification-config")

urlpatterns = [
    path("monitoring/task-logs/", TaskLogListView.as_view(), name="task-logs"),
    path("", include(router.urls)),
]
