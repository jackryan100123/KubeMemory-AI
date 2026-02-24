"""Development settings for KubeMemory."""
from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Ensure SPA on :5173 can POST (Django 4+ origin check)
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
