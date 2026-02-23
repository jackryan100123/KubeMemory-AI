"""
Celery app configuration for KubeMemory. Auto-discovers tasks from all installed apps.
"""
from celery import Celery
from django.conf import settings

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(lambda: [a for a in settings.INSTALLED_APPS if a.startswith("apps.")])


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f"Request: {self.request!r}")
