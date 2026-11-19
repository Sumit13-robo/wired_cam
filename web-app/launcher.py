"""Windows entry point: starts WiredCam locally and opens the dashboard."""
from __future__ import annotations

import threading
import time
import webbrowser

import uvicorn


def open_dashboard() -> None:
    time.sleep(0.8)
    webbrowser.open("http://127.0.0.1:8765", new=1)


if __name__ == "__main__":
    threading.Thread(target=open_dashboard, daemon=True).start()
    uvicorn.run("server:app", host="127.0.0.1", port=8765, log_level="warning")
