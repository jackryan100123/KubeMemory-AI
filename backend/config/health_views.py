"""Public health check endpoint (no authentication required)."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request: Request) -> Response:
    """Liveness probe for load balancers and CI smoke tests."""
    return Response({"status": "ok"})
