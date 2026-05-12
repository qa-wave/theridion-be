"""Integrations: send notifications to Slack, Teams, or custom webhooks."""

from __future__ import annotations

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class NotifyInput(BaseModel):
    provider: str  # "slack" | "teams" | "webhook"
    url: str
    message: str
    payload: dict | None = None


class NotifyOutput(BaseModel):
    ok: bool
    status_code: int = 0
    error: str | None = None


@router.post("/notify", response_model=NotifyOutput)
async def notify(body: NotifyInput) -> NotifyOutput:
    try:
        if body.provider == "slack":
            payload = body.payload or {"text": body.message}
        elif body.provider == "teams":
            payload = body.payload or {"text": body.message}
        else:
            payload = body.payload or {"message": body.message}

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(body.url, json=payload)
        return NotifyOutput(ok=resp.status_code < 400, status_code=resp.status_code)
    except Exception as exc:
        return NotifyOutput(ok=False, error=str(exc))
