"""WebSocket consumer for real-time incident push to React frontend."""
import json

from channels.generic.websocket import AsyncWebsocketConsumer


class IncidentConsumer(AsyncWebsocketConsumer):
    """Consumes incident alerts and analysis events; pushes to connected clients."""

    GROUP_NAME = "incidents"

    async def connect(self) -> None:
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    async def incident_alert(self, event: dict) -> None:
        """Called by Celery tasks via channel layer to push to all connected clients."""
        event_type = event.get("event_type", "new_incident")
        await self.send(
            text_data=json.dumps(
                {
                    "type": event_type,
                    "data": event["incident"],
                }
            )
        )

    async def incident_updated(self, event: dict) -> None:
        """Called when a deduplicated incident occurrence_count increases."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "incident_updated",
                    "data": event["incident"],
                }
            )
        )

    async def analysis_complete(self, event: dict) -> None:
        """Called when LangGraph analysis finishes."""
        await self.send(text_data=json.dumps({
            "type": "analysis_complete",
            "incident_id": event["incident_id"],
            "analysis": event.get("analysis", ""),
            "root_cause": event.get("root_cause", ""),
            "confidence": event.get("confidence", 0.0),
            "sources": event.get("sources", []),
        }))
