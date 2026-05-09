"""FastAPI sidecar entrypoint.

Runs as a localhost-only HTTP server consumed by the Tauri shell over
loopback. Port is selected dynamically and printed to stdout on startup so
the parent process can read it; if THERIDION_PORT is set, that port is used
instead (handy in dev).
"""

from __future__ import annotations

import atexit
import os
import socket
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from theridion_sidecar import __version__, storage
from theridion_sidecar.api.assertions import router as assertions_router
from theridion_sidecar.api.collections import router as collections_router
from theridion_sidecar.api.cookies import router as cookies_router
from theridion_sidecar.api.curl import router as curl_router
from theridion_sidecar.api.diagnostics import router as diagnostics_router
from theridion_sidecar.api.environments import router as environments_router
from theridion_sidecar.api.graphql import router as graphql_router
from theridion_sidecar.api.health import router as health_router
from theridion_sidecar.api.requests import router as requests_router
from theridion_sidecar.api.runner import router as runner_router
from theridion_sidecar.api.soap import router as soap_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Theridion sidecar",
        version=__version__,
        docs_url="/docs",
        redoc_url=None,
    )

    # We only ever bind to 127.0.0.1, so any HTTP origin reaching us is
    # already loopback-only. Match any localhost / 127.0.0.1 port via
    # regex so dev (1420), Playwright tests (1421), and the Vite fallback
    # (5173) all work without enumerating ports here. Tauri's custom
    # protocols are matched explicitly.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=(
            r"^(?:https?://(?:localhost|127\.0\.0\.1)(?::\d+)?"
            r"|tauri://localhost"
            r"|https://tauri\.localhost)$"
        ),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(requests_router)
    app.include_router(assertions_router)
    app.include_router(runner_router)
    app.include_router(collections_router)
    app.include_router(environments_router)
    app.include_router(graphql_router)
    app.include_router(soap_router)
    app.include_router(cookies_router)
    app.include_router(curl_router)
    app.include_router(diagnostics_router)
    return app


app = create_app()


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _write_pid_file(port: int) -> None:
    """Write `pid:port` to the storage dir so callers can locate the live
    sidecar. Best-effort: if we can't write it, log and continue."""
    pid_path = storage.home_dir() / "sidecar.pid"
    try:
        storage.home_dir().mkdir(parents=True, exist_ok=True)
        pid_path.write_text(f"{os.getpid()}:{port}\n", encoding="utf-8")
    except OSError as e:
        print(f"warning: could not write {pid_path}: {e}", file=sys.stderr)
        return

    def _cleanup() -> None:
        try:
            current = pid_path.read_text(encoding="utf-8").strip()
            # Only remove if it's still our entry — don't clobber a successor.
            if current.startswith(f"{os.getpid()}:"):
                pid_path.unlink(missing_ok=True)
        except OSError:
            pass

    atexit.register(_cleanup)


def main() -> None:
    port_env = os.environ.get("THERIDION_PORT")
    port = int(port_env) if port_env else _pick_free_port()
    _write_pid_file(port)
    # Print on a single line so the Tauri parent can parse it deterministically.
    # Includes pid so a misbehaving instance can be killed without grep
    # gymnastics.
    print(
        f"THERIDION_SIDECAR_READY pid={os.getpid()} port={port} "
        f"home={storage.home_dir()}",
        flush=True,
    )
    uvicorn.run(
        "theridion_sidecar.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    sys.exit(main())
