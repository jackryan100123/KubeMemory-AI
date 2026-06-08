"""
DRF permission helpers for KubeMemory API authentication and cluster RBAC.
"""
from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

PUBLIC_API_PATHS: frozenset[str] = frozenset(
    {
        "/api/token/",
        "/api/token/refresh/",
        "/api/health/",
    }
)


def is_public_api_path(path: str) -> bool:
    """Return True if path is a whitelisted unauthenticated API route."""
    normalized = path if path.endswith("/") else f"{path}/"
    return normalized in PUBLIC_API_PATHS


class IsAuthenticatedOrPublicPath(BasePermission):
    """Allow JWT auth everywhere except whitelisted public API paths."""

    def has_permission(self, request: Request, view: Any) -> bool:
        if is_public_api_path(request.path):
            return True
        return bool(request.user and request.user.is_authenticated)


def get_user_role(user) -> str:
    """Return role from UserProfile; default viewer."""
    if not user or not getattr(user, "is_authenticated", False):
        return "viewer"
    profile = getattr(user, "profile", None)
    if profile is None:
        return "viewer"
    return profile.role


def has_operator_permission(user) -> bool:
    """Operator or admin may start/stop watchers and connect clusters."""
    return get_user_role(user) in ("operator", "admin")


class IsClusterOperator(BasePermission):
    """Require operator/admin for mutating cluster watcher actions."""

    def has_permission(self, request: Request, view: Any) -> bool:
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return bool(request.user and request.user.is_authenticated)
        return has_operator_permission(request.user)


class CanMutateClusterEnvironment(BasePermission):
    """Viewers cannot mutate production cluster resources."""

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        role = get_user_role(request.user)
        if role == "viewer":
            return getattr(obj, "environment", None) != "prod"
        return has_operator_permission(request.user)

    def has_permission(self, request: Request, view: Any) -> bool:
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return bool(request.user and request.user.is_authenticated)
        return has_operator_permission(request.user)
