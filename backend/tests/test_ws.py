"""WebSocket incident broadcast tests."""
import pytest
from channels.testing import WebsocketCommunicator

from config.asgi import application


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_ws_incidents_connect() -> None:
    communicator = WebsocketCommunicator(application, "/ws/incidents/")
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()
