"""Domain models shared across endpoints and storage.

Pydantic models double as both the wire schema (FastAPI generates the
OpenAPI for them) and the on-disk schema (we serialize directly with
`.model_dump()`).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

HttpMethod = Literal[
    "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"
]


class SavedRequest(BaseModel):
    id: str
    name: str
    method: HttpMethod = "GET"
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None


class Collection(BaseModel):
    id: str
    name: str
    version: int = 1
    items: list[SavedRequest] = Field(default_factory=list)


class CollectionSummary(BaseModel):
    """Lightweight projection used by the list endpoint."""
    id: str
    name: str
    request_count: int


# Request bodies for write endpoints
class CreateCollectionInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class SaveRequestInput(BaseModel):
    id: str | None = None  # server assigns if omitted
    name: str = Field(..., min_length=1, max_length=200)
    method: HttpMethod = "GET"
    url: str = Field(..., min_length=1)
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
