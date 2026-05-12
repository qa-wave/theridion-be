"""JMS client: stub endpoints for future Java bridge integration."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/jms", tags=["jms"])


class JmsStubOutput(BaseModel):
    status: str = "not_available"
    message: str = "JMS requires Java runtime"


@router.post("/send", response_model=JmsStubOutput)
async def jms_send() -> JmsStubOutput:
    return JmsStubOutput()


@router.post("/receive", response_model=JmsStubOutput)
async def jms_receive() -> JmsStubOutput:
    return JmsStubOutput()
