"""MQTT client: stub endpoints for future paho-mqtt integration."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/mqtt", tags=["mqtt"])


class MqttStubOutput(BaseModel):
    status: str = "not_available"
    message: str = "MQTT support requires paho-mqtt. Install it to enable."


@router.post("/connect", response_model=MqttStubOutput)
async def mqtt_connect() -> MqttStubOutput:
    return MqttStubOutput()


@router.post("/publish", response_model=MqttStubOutput)
async def mqtt_publish() -> MqttStubOutput:
    return MqttStubOutput()


@router.post("/subscribe", response_model=MqttStubOutput)
async def mqtt_subscribe() -> MqttStubOutput:
    return MqttStubOutput()
