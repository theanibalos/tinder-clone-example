import json
from core.base_plugin import BasePlugin


class ChatWsPlugin(BasePlugin):
    """WebSocket chat plugin: real-time messaging for matched users."""

    def __init__(self, http, db, auth, event_bus, logger):
        self.http = http
        self.db = db
        self.auth = auth
        self.bus = event_bus
        self.logger = logger
        self._connections = {}  # match_id -> {user_id: websocket}

    async def on_boot(self):
        self.http.add_ws_endpoint(
            "/ws/chat/{match_id}",
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
        )
        await self.bus.subscribe("message.sent", self._on_message_event)

    async def _on_connect(self, ws, path_params=None):
        """Handles WebSocket connection. Expects token as first message."""
        try:
            # Wait for auth message
            auth_msg = await ws.receive_text()
            auth_data = json.loads(auth_msg)
            token = auth_data.get("token")

            if not token:
                await ws.send_text(json.dumps({"error": "Token required"}))
                await ws.close()
                return

            try:
                payload = self.auth.decode_token(token)
            except Exception:
                await ws.send_text(json.dumps({"error": "Invalid token"}))
                await ws.close()
                return

            user_id = int(payload.get("sub"))
            match_id = int(path_params.get("match_id")) if path_params else None

            if not match_id:
                await ws.send_text(json.dumps({"error": "Match ID required"}))
                await ws.close()
                return

            # Verify match membership
            match = await self.db.query_one(
                """SELECT id FROM matches
                   WHERE id = $1 AND (user_a_id = $2 OR user_b_id = $3) AND is_active = 1""",
                [match_id, user_id, user_id]
            )
            if not match:
                await ws.send_text(json.dumps({"error": "Match not found or inactive"}))
                await ws.close()
                return

            # Register connection
            if match_id not in self._connections:
                self._connections[match_id] = {}
            self._connections[match_id][user_id] = ws

            await ws.send_text(json.dumps({"type": "connected", "match_id": match_id}))
            self.logger.info(f"WebSocket connected: user {user_id} in match {match_id}")

            # Message loop
            while True:
                try:
                    raw = await ws.receive_text()
                    msg_data = json.loads(raw)

                    if msg_data.get("type") == "message":
                        content = msg_data.get("content", "")
                        content_type = msg_data.get("content_type", "text")

                        msg_id = await self.db.execute(
                            """INSERT INTO messages (match_id, sender_id, content, content_type)
                               VALUES ($1, $2, $3, $4) RETURNING id""",
                            [match_id, user_id, content, content_type]
                        )

                        broadcast = json.dumps({
                            "type": "message",
                            "id": msg_id,
                            "match_id": match_id,
                            "sender_id": user_id,
                            "content": content,
                            "content_type": content_type,
                        })

                        # Send to all connections in this match
                        for uid, conn in self._connections.get(match_id, {}).items():
                            try:
                                await conn.send_text(broadcast)
                            except Exception:
                                pass

                    elif msg_data.get("type") == "typing":
                        # Broadcast typing indicator
                        for uid, conn in self._connections.get(match_id, {}).items():
                            if uid != user_id:
                                try:
                                    await conn.send_text(json.dumps({
                                        "type": "typing",
                                        "user_id": user_id,
                                    }))
                                except Exception:
                                    pass

                    elif msg_data.get("type") == "read":
                        msg_id = msg_data.get("message_id")
                        if msg_id:
                            await self.db.execute(
                                "UPDATE messages SET is_read = 1 WHERE id = $1 AND match_id = $2",
                                [msg_id, match_id]
                            )

                except Exception:
                    break

        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")

    async def _on_disconnect(self, ws, path_params=None):
        """Clean up connection on disconnect."""
        # Remove from connections map
        for match_id, users in list(self._connections.items()):
            for user_id, conn in list(users.items()):
                if conn is ws:
                    del self._connections[match_id][user_id]
                    if not self._connections[match_id]:
                        del self._connections[match_id]
                    self.logger.info(f"WebSocket disconnected: user {user_id} from match {match_id}")
                    return

    async def _on_message_event(self, data: dict):
        """Relay messages from REST API to WebSocket connections."""
        match_id = data.get("match_id")
        sender_id = data.get("sender_id")

        if match_id in self._connections:
            broadcast = json.dumps({
                "type": "message",
                "id": data.get("id"),
                "match_id": match_id,
                "sender_id": sender_id,
                "content": data.get("content"),
                "content_type": data.get("content_type"),
            })

            for uid, conn in self._connections.get(match_id, {}).items():
                if uid != sender_id:  # Don't echo back to sender (they sent via REST)
                    try:
                        await conn.send_text(broadcast)
                    except Exception:
                        pass
