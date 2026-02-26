"""
Bridge Point — WebSocket Manager
Real-time notifications and WebRTC call signaling relay.
"""

import json
from typing import Dict, Set, Optional
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections per user and relays call signaling."""

    def __init__(self):
        self._connections: Dict[int, Set[WebSocket]] = {}
        # Track active calls: user_id -> call_id they are currently in
        self._active_calls: Dict[int, int] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept and register a WebSocket connection for a user."""
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection."""
        if user_id in self._connections:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]

    def is_online(self, user_id: int) -> bool:
        """Check if a user has any active WebSocket connections."""
        return user_id in self._connections and len(self._connections[user_id]) > 0

    def is_in_call(self, user_id: int) -> bool:
        """Check if a user is currently in an active call."""
        return user_id in self._active_calls

    def set_in_call(self, user_id: int, call_id: int):
        """Mark a user as being in an active call."""
        self._active_calls[user_id] = call_id

    def clear_call(self, user_id: int):
        """Clear a user's active call status."""
        self._active_calls.pop(user_id, None)

    def get_active_call_id(self, user_id: int) -> Optional[int]:
        """Get the call ID a user is currently in, or None."""
        return self._active_calls.get(user_id)

    async def send_to_user(self, user_id: int, message: dict):
        """Send a JSON message to all connections of a specific user."""
        if user_id not in self._connections:
            return
        dead_connections = set()
        for ws in self._connections[user_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.add(ws)
        # Clean up dead connections
        for ws in dead_connections:
            self._connections[user_id].discard(ws)

    async def relay_to_user(
        self, from_user_id: int, to_user_id: int, message: dict
    ) -> bool:
        """
        Relay a signaling message from one user to another.
        Returns True if the target user is online and message was sent.
        """
        if not self.is_online(to_user_id):
            # Notify caller that target is offline
            await self.send_to_user(from_user_id, {
                "type": "call:user_offline",
                "user_id": to_user_id,
            })
            return False

        # Attach sender info and forward
        message["from_user_id"] = from_user_id
        await self.send_to_user(to_user_id, message)
        return True

    async def broadcast_to_users(self, user_ids: list[int], message: dict):
        """Send a message to multiple users."""
        for user_id in user_ids:
            await self.send_to_user(user_id, message)

    @property
    def active_connections_count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())


# Singleton instance
manager = ConnectionManager()
