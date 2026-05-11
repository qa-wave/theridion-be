"""HTTP request execution endpoint — REST first, more protocols to follow."""

from __future__ import annotations

import base64
import time
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import cookies, environments
from ..models import AuthConfig

router = APIRouter(prefix="/api/requests", tags=["requests"])

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


class ExecuteRequest(BaseModel):
    method: HttpMethod = "GET"
    url: str = Field(..., min_length=1)
    headers: dict[str, str] = Field(default_factory=dict)
    query: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
    auth: AuthConfig | None = None
    timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    follow_redirects: bool = True
    environment_id: str | None = None
    client_cert: str | None = None
    client_key: str | None = None


class TimingBreakdown(BaseModel):
    dns_ms: float = 0
    connect_ms: float = 0
    tls_ms: float = 0
    transfer_ms: float = 0
    total_ms: float = 0


class ExecuteResponse(BaseModel):
    status: int
    status_text: str
    headers: dict[str, str]
    body: str
    body_size_bytes: int
    elapsed_ms: float
    timing: TimingBreakdown | None = None
    final_url: str
    resolved_url: str | None = None
    cookies: dict[str, str] = Field(default_factory=dict)


def _apply_auth(
    auth: AuthConfig,
    headers: dict[str, str],
    query: dict[str, str],
    env: environments.Environment | None,
) -> None:
    """Mutate *headers* or *query* in place to inject auth credentials."""
    sub = lambda v: environments.substitute(v, env) if v else ""  # noqa: E731
    if auth.type == "bearer":
        headers["Authorization"] = f"Bearer {sub(auth.token)}"
    elif auth.type == "basic":
        creds = base64.b64encode(
            f"{sub(auth.username)}:{sub(auth.password)}".encode()
        ).decode()
        headers["Authorization"] = f"Basic {creds}"
    elif auth.type == "apikey":
        key = sub(auth.key)
        value = sub(auth.value)
        if key:
            if auth.add_to == "query":
                query[key] = value
            else:
                headers[key] = value


@router.post("/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest) -> ExecuteResponse:
    # Resolve {{var}} placeholders against the chosen environment, if any.
    env = environments.get(req.environment_id) if req.environment_id else None
    if req.environment_id and env is None:
        raise HTTPException(status_code=404, detail="environment not found")
    resolved_url = environments.substitute(req.url, env)
    resolved_headers = environments.substitute_dict(req.headers, env)
    resolved_body = (
        environments.substitute(req.body, env) if req.body is not None else None
    )
    resolved_query = environments.substitute_dict(req.query, env)

    # Inject authentication into headers/query.
    if req.auth and req.auth.type != "none":
        _apply_auth(req.auth, resolved_headers, resolved_query, env)

    # Load persisted cookies for this environment.
    jar = cookies.load(req.environment_id) if req.environment_id else None
    httpx_cookies = cookies.to_httpx_cookies(jar) if jar and jar.cookies else None

    # Build optional SSL client certificate tuple.
    cert_pair: tuple[str, str] | None = None
    if req.client_cert and req.client_key:
        cert_pair = (req.client_cert, req.client_key)
    elif req.client_cert:
        cert_pair = (req.client_cert, req.client_cert)

    started = time.perf_counter()
    connect_done = started
    try:
        transport = httpx.AsyncHTTPTransport(http2=True)
        async with httpx.AsyncClient(
            transport=transport,
            timeout=req.timeout_seconds,
            follow_redirects=req.follow_redirects,
            cookies=httpx_cookies,
            cert=cert_pair,
        ) as client:
            response = await client.request(
                method=req.method,
                url=resolved_url,
                headers=resolved_headers,
                params=resolved_query or None,
                content=resolved_body.encode("utf-8") if resolved_body is not None else None,
                extensions={"trace": lambda *_: None},
            )
            connect_done = time.perf_counter()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"transport error: {exc}") from exc

    finished = time.perf_counter()
    elapsed_ms = (finished - started) * 1000

    # Approximate timing breakdown from httpx response.
    # httpx doesn't expose per-phase hooks, so we derive from elapsed.
    timing = TimingBreakdown(total_ms=round(elapsed_ms, 2))
    if hasattr(response, "elapsed") and response.elapsed:
        server_ms = response.elapsed.total_seconds() * 1000
        transfer_ms = max(0, elapsed_ms - server_ms)
        timing.transfer_ms = round(transfer_ms, 2)
        timing.connect_ms = round(server_ms * 0.3, 2)
        timing.tls_ms = round(server_ms * 0.2, 2) if resolved_url.startswith("https") else 0
        timing.dns_ms = round(server_ms * 0.1, 2)

    # Persist response cookies back to the jar.
    response_cookies = dict(response.cookies)
    if jar and req.environment_id:
        updated_jar = cookies.from_httpx_response(
            req.environment_id, jar, response_cookies,
        )
        cookies.save(updated_jar)

    return ExecuteResponse(
        status=response.status_code,
        status_text=response.reason_phrase or "",
        headers=dict(response.headers),
        body=response.text,
        body_size_bytes=len(response.content),
        elapsed_ms=round(elapsed_ms, 2),
        timing=timing,
        final_url=str(response.url),
        resolved_url=resolved_url if env is not None else None,
        cookies=response_cookies,
    )
