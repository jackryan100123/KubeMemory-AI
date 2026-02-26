"""WebSocket consumer for the cluster chat assistant."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.chat.agent import run_chat_agent

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Real-time chat with the cluster assistant. Receives messages, runs agent, streams reply."""

    async def connect(self) -> None:
        self._loop = asyncio.get_event_loop()
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        pass

    async def receive_json(self, content: dict) -> None:
        message = content.get("message") or content.get("text") or ""
        history = content.get("history") or []
        cluster_id = content.get("cluster_id")
        cluster_name = content.get("cluster_name") or ""
        if not message or not isinstance(message, str):
            await self.send_json({"type": "error", "message": "Missing or invalid 'message'."})
            return

        def stream_cb(event: str, data: dict) -> None:
            payload = {"type": event, **data}
            asyncio.run_coroutine_threadsafe(self._send_json(payload), self._loop)

        def run_agent() -> None:
            try:
                run_chat_agent(
                    user_message=message,
                    history=history,
                    stream_callback=stream_cb,
                    cluster_id=cluster_id,
                    cluster_name=cluster_name,
                )
                # Agent sends "done" via stream_cb; ensure we never leave client loading if it didn't
            except Exception as e:
                logger.exception("Chat agent failed: %s", e)
                asyncio.run_coroutine_threadsafe(
                    self._send_json({"type": "error", "message": str(e)}),
                    self._loop,
                )

        try:
            await asyncio.get_event_loop().run_in_executor(_executor, run_agent)
        except Exception as e:
            logger.exception("Chat executor failed: %s", e)
            await self.send_json({"type": "error", "message": str(e)})

    async def _send_json(self, payload: dict) -> None:
        """Send JSON to the client (must run on async loop)."""
        try:
            await self.send_json(payload)
        except Exception as e:
            logger.warning("_send_json: %s", e)
