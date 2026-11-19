"""Local-only WiredCam web bridge. It runs ADB and never exposes the phone stream remotely."""
from __future__ import annotations

import asyncio
import json
import shutil
import socket
import struct
import subprocess
import sys
import time
from fractions import Fraction
from contextlib import suppress
from io import BytesIO
from pathlib import Path

import av
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# PyInstaller extracts web assets into _MEIPASS; source runs use this directory.
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
HEADER = struct.Struct(">BBQI")
VIDEO_CONFIG, VIDEO_FRAME, CONTROL = 1, 2, 16


def adb() -> str | None:
    bundled = ROOT / "platform-tools" / "adb.exe"
    return str(bundled) if bundled.exists() else shutil.which("adb")


def usb_device() -> tuple[str, str | None]:
    program = adb()
    if not program:
        return "ADB not found. Install Android Platform Tools or place it in web-app/platform-tools.", None
    try:
        output = subprocess.run([program, "devices"], capture_output=True, text=True, timeout=8).stdout
    except OSError as exc:
        return f"Could not run ADB: {exc}", None
    entries = [line.split() for line in output.splitlines()[1:] if line.strip()]
    if not entries:
        return "No Android device found. Connect USB and enable USB debugging.", None
    serial, state = entries[0][0], entries[0][1]
    if state == "unauthorized":
        return "Unlock the phone and accept the USB debugging prompt.", None
    if state != "device":
        return f"Android reports device state: {state}.", None
    return f"Phone connected via USB ({serial}).", serial


class Bridge:
    def __init__(self) -> None:
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.task: asyncio.Task | None = None
        self.clients: set[WebSocket] = set()
        self.state = "Ready to connect"
        self.decoder = av.CodecContext.create("h264", "r")
        self.connected_at = 0.0
        self.frames = 0

    def status(self) -> dict:
        message, serial = usb_device()
        return {"state": self.state, "device": message, "serial": serial, "connected": self.writer is not None}

    async def connect(self, host: str, port: int, via_adb: bool) -> None:
        await self.disconnect()
        if via_adb:
            message, serial = usb_device()
            if not serial:
                raise HTTPException(409, message)
            completed = await asyncio.to_thread(subprocess.run, [adb(), "-s", serial, "forward", f"tcp:{port}", f"tcp:{port}"], capture_output=True, text=True, timeout=10)
            if completed.returncode:
                raise HTTPException(502, completed.stderr.strip() or "ADB forwarding failed")
            host = "127.0.0.1"
        try:
            self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=6)
        except OSError as exc:
            self.reader = self.writer = None
            raise HTTPException(502, f"Could not reach phone stream: {exc}")
        self.decoder = av.CodecContext.create("h264", "r")
        self.state = "Live"
        self.connected_at = time.monotonic(); self.frames = 0
        self.task = asyncio.create_task(self.read_loop())

    async def disconnect(self) -> None:
        if self.task:
            self.task.cancel()
            with suppress(asyncio.CancelledError): await self.task
        self.task = None
        if self.writer:
            self.writer.close()
            with suppress(Exception): await self.writer.wait_closed()
        self.reader = self.writer = None
        if self.state == "Live": self.state = "Disconnected"

    async def send_control(self, payload: dict) -> None:
        if not self.writer:
            raise HTTPException(409, "Connect to a phone first.")
        data = json.dumps(payload, separators=(",", ":")).encode()
        self.writer.write(HEADER.pack(CONTROL, 0, 0, len(data)) + data)
        await self.writer.drain()

    async def read_loop(self) -> None:
        try:
            assert self.reader
            while True:
                kind, flags, pts, length = HEADER.unpack(await self.reader.readexactly(14))
                if length > 16 * 1024 * 1024: raise ValueError("Phone sent an invalid packet length")
                payload = await self.reader.readexactly(length)
                if kind == CONTROL:
                    continue
                if kind not in (VIDEO_CONFIG, VIDEO_FRAME):
                    continue
                packet = av.Packet(payload); packet.pts = packet.dts = pts
                packet.time_base = Fraction(1, 1_000_000)
                for frame in self.decoder.decode(packet):
                    image = frame.to_image(); buffer = BytesIO(); image.save(buffer, "JPEG", quality=78, optimize=True)
                    self.frames += 1
                    await self.broadcast(buffer.getvalue())
        except (asyncio.IncompleteReadError, ConnectionError, OSError, ValueError, av.FFmpegError) as exc:
            self.state = f"Stream stopped: {exc}"
        except asyncio.CancelledError:
            raise
        finally:
            self.reader = self.writer = None

    async def broadcast(self, frame: bytes) -> None:
        stale: list[WebSocket] = []
        for client in self.clients:
            try: await client.send_bytes(frame)
            except Exception: stale.append(client)
        for client in stale: self.clients.discard(client)


bridge = Bridge()
app = FastAPI(title="WiredCam Local")
app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")

@app.get("/")
async def home(): return FileResponse(ROOT / "index.html")

@app.get("/api/status")
async def status(): return bridge.status()

@app.post("/api/connect")
async def connect(body: dict):
    await bridge.connect(str(body.get("host", "127.0.0.1")), int(body.get("port", 5555)), bool(body.get("viaAdb", True)))
    return bridge.status()

@app.post("/api/disconnect")
async def disconnect(): await bridge.disconnect(); return bridge.status()

@app.post("/api/control")
async def control(body: dict): await bridge.send_control(body); return {"ok": True}

@app.websocket("/ws/preview")
async def preview(websocket: WebSocket):
    await websocket.accept(); bridge.clients.add(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: pass
    finally: bridge.clients.discard(websocket)
