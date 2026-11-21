"""Wizard Arena Online — minimal, private-room WebSocket relay.

Run: python -m pip install -r requirements.txt && python server.py
Works behind a TLS proxy: https://HOST/health and wss://HOST/ws.

Only in-memory room membership is stored. No registration or player names.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from http import HTTPStatus
import json
import logging
import os
import secrets
import signal
import time

from websockets.asyncio.server import serve, ServerConnection
from websockets.exceptions import ConnectionClosed

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8765"))
MAX_ROOMS = int(os.environ.get("MAX_ROOMS", "200"))
MAX_CLIENTS = int(os.environ.get("MAX_CLIENTS", "450"))
MAX_RELAY_BYTES = 48000
ROOM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
RELAY_TYPES = {"welcome", "hello", "room", "select", "ready", "start",
               "input", "cast", "state", "finish", "leaveGame"}
logger = logging.getLogger("wizard-relay")


@dataclass
class Room:
    code: str
    host: ServerConnection
    guest: ServerConnection | None = None


rooms: dict[str, Room] = {}
clients: set[ServerConnection] = set()
# Client state maps websocket -> (room code, role).
member: dict[ServerConnection, tuple[str, str]] = {}


def encode(message: dict) -> str:
    return json.dumps(message, separators=(",", ":"), ensure_ascii=True)


async def send(client: ServerConnection | None, data: dict) -> None:
    if client is None:
        return
    try:
        await client.send(encode(data))
    except ConnectionClosed:
        pass


def create_code() -> str:
    for _ in range(30):
        code = "".join(secrets.choice(ROOM_ALPHABET) for _ in range(6))
        if code not in rooms:
            return code
    raise RuntimeError("room code allocation failed")


async def cleanup(client: ServerConnection) -> None:
    info = member.pop(client, None)
    clients.discard(client)
    if not info:
        return
    code, role = info
    room = rooms.get(code)
    if room is None:
        return
    if role == "host" and room.host is client:
        rooms.pop(code, None)
        guest = room.guest
        if guest is not None:
            member.pop(guest, None)
            await send(guest, {"type": "room_closed", "message": "The host closed this room."})
            try:
                await guest.close(code=1000, reason="Room closed")
            except ConnectionClosed:
                pass
    elif role == "guest" and room.guest is client:
        room.guest = None
        await send(room.host, {"type": "peer_left", "message": "Player 2 left. The room remains open."})


async def handle(client: ServerConnection) -> None:
    if len(clients) >= MAX_CLIENTS:
        await send(client, {"type": "error", "message": "Relay is full. Try again later."})
        await client.close(code=1013, reason="Server busy")
        return
    clients.add(client)
    joined_at = time.monotonic()
    last_messages: list[float] = []
    try:
        async for raw in client:
            if not isinstance(raw, str) or len(raw) > MAX_RELAY_BYTES:
                await send(client, {"type": "error", "message": "Invalid or oversized message."})
                continue
            try:
                message = json.loads(raw)
            except (ValueError, TypeError):
                await send(client, {"type": "error", "message": "Invalid JSON."})
                continue
            if not isinstance(message, dict):
                continue
            now = time.monotonic()
            last_messages[:] = [t for t in last_messages if now - t < 1.0]
            last_messages.append(now)
            if len(last_messages) > 65:
                await send(client, {"type": "error", "message": "Too many messages per second."})
                await client.close(code=1008, reason="Rate limit")
                break
            kind = message.get("type")
            if kind == "ping":
                await send(client, {"type": "pong"})
            elif kind == "create" and client not in member:
                if len(rooms) >= MAX_ROOMS:
                    await send(client, {"type": "error", "message": "Too many active rooms. Try later."})
                    continue
                code = create_code()
                rooms[code] = Room(code, client)
                member[client] = (code, "host")
                await send(client, {"type": "created", "code": code})
                logger.info("room created (active rooms: %d)", len(rooms))
            elif kind == "join" and client not in member:
                code = str(message.get("code", "")).strip().upper()
                if len(code) != 6 or any(c not in ROOM_ALPHABET for c in code):
                    await send(client, {"type": "error", "message": "Enter a valid six-character room code."})
                    continue
                room = rooms.get(code)
                if room is None:
                    await send(client, {"type": "error", "message": "Room not found. Check the code and relay server."})
                elif room.guest is not None:
                    await send(client, {"type": "error", "message": "This room already has two players."})
                else:
                    room.guest = client
                    member[client] = (code, "guest")
                    # Guest must be initialized before host can relay a welcome.
                    await send(client, {"type": "joined", "code": code})
                    await send(room.host, {"type": "peer_joined"})
                    logger.info("player joined a room")
            elif kind == "relay" and client in member:
                code, role = member[client]
                room = rooms.get(code)
                if room is None:
                    continue
                data = message.get("payload")
                if not isinstance(data, dict) or data.get("v") != 1 or data.get("t") not in RELAY_TYPES:
                    continue
                recipient = room.guest if role == "host" else room.host
                if recipient is not None:
                    await send(recipient, {"type": "relay", "payload": data})
            else:
                await send(client, {"type": "error", "message": "Invalid action for this connection."})
    except ConnectionClosed:
        pass
    except Exception:
        logger.exception("Unexpected relay client error")
    finally:
        await cleanup(client)
        logger.debug("client closed after %.1fs", time.monotonic() - joined_at)


def process_request(connection: ServerConnection, request):
    if request.path == "/health":
        return connection.respond(HTTPStatus.OK, "Wizard Arena relay is running\n")
    if request.path not in ("/ws", "/ws/"):
        return connection.respond(HTTPStatus.NOT_FOUND, "Use /ws for WebSocket or /health for status.\n")
    return None


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("Wizard Arena relay starting at %s:%s", HOST, PORT)
    async with serve(handle, HOST, PORT, process_request=process_request,
                     max_size=MAX_RELAY_BYTES, ping_interval=20, ping_timeout=20,
                     compression=None, server_header=None) as server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
