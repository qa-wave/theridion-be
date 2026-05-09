"""FastAPI sidecar entrypoint.

Runs as a localhost-only HTTP server consumed by the Tauri shell over
loopback. Port is selected dynamically and printed to stdout on startup so
the parent process can read it; if THERIDION_PORT is set, that port is used
instead (handy in dev).
"""

from __future__ import annotations

import os
import socket
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from theridion_sidecar import __version__
from theridion_sidecar.api.collections import router as collections_router
from theridion_sidecar.api.health import router as health_router
from theridion_sidecar.api.requests import router as requests_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Theridion sidecar",
        version=__version__,
        docs_url="/docs",
        redoc_url=None,
    )

    # In dev, the Vite dev server (5173) talks to us. In production, the
    # Tauri shell uses tauri://localhost. Loopback-only is enforced by
    # binding to 127.0.0.1; CORS is permissive against that loopback origin
    # set.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:1420",   # tauri dev
            "http://localhost:5173",   # vite dev fallback
            "tauri://localhost",
            "https://tauri.localhost",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(requests_router)
    app.include_router(collections_router)
    return app


app = create_app()


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    port_env = os.environ.get("THERIDION_PORT")
    port = int(port_env) if port_env else _pick_free_port()
    # Print on a single line so the Tauri parent can parse it deterministically.
    print(f"THERIDION_SIDECAR_READY port={port}", flush=True)
    uvicorn.run(
        "theridion_sidecar.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    sys.exit(main())
