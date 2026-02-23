"""URL routing for memory app (Phase 2)."""
from django.urls import path

from . import views

urlpatterns = [
    path("memory/search/", views.MemorySearchView.as_view(), name="memory-search"),
    path("memory/graph/", views.MemoryGraphView.as_view(), name="memory-graph"),
    path("memory/patterns/", views.MemoryPatternsView.as_view(), name="memory-patterns"),
    path("memory/blast-radius/", views.MemoryBlastRadiusView.as_view(), name="memory-blast-radius"),
]
