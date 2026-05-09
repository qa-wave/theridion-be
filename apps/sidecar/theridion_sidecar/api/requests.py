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


class ExecuteResponse(BaseModel):
    status: int
    status_text: str
    headers: dict[str, str]
    body: str
    body_size_bytes: int
    elapsed_ms: float
    final_url: str
    # Echo back the URL after env-var substitution — handy for debugging
    # "why didn't my {{baseUrl}} resolve" without re-running the request.
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

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(
            http2=True,
            timeout=req.timeout_seconds,
            follow_redirects=req.follow_redirects,
            cookies=httpx_cookies,
        ) as client:
            response = await client.request(
                method=req.method,
                url=resolved_url,
                headers=resolved_headers,
                params=resolved_query or None,
                content=resolved_body.encode("utf-8") if resolved_body is not None else None,
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"transport error: {exc}") from exc

    # Persist response cookies back to the jar.
    response_cookies = dict(response.cookies)
    if jar and req.environment_id:
        updated_jar = cookies.from_httpx_response(
            req.environment_id, jar, response_cookies,
        )
        cookies.save(updated_jar)

    elapsed_ms = (time.perf_counter() - started) * 1000
    return ExecuteResponse(
        status=response.status_code,
        status_text=response.reason_phrase or "",
        headers=dict(response.headers),
        body=response.text,
        body_size_bytes=len(response.content),
        elapsed_ms=round(elapsed_ms, 2),
        final_url=str(response.url),
        resolved_url=resolved_url if env is not None else None,
        cookies=response_cookies,
    )
