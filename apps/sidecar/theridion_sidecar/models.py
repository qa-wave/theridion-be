"""Domain models shared across endpoints and storage.

The collection tree is a discriminated union of folders and requests
through a single `CollectionItem` model with `is_folder`. Older files
predating folders deserialize cleanly because `is_folder` defaults to
False and `items` defaults to an empty list.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

HttpMethod = Literal[
    "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"
]


class CollectionItem(BaseModel):
    """Either a folder (is_folder=True, has child items) or a request."""
    id: str
    name: str
    is_folder: bool = False
    # Request-specific fields (populated when is_folder=False).
    method: HttpMethod | None = None
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
    # Folder-specific field (populated when is_folder=True).
    items: list["CollectionItem"] = Field(default_factory=list)


CollectionItem.model_rebuild()


# Back-compat alias used by the older /requests endpoint contract.
SavedRequest = CollectionItem


class Collection(BaseModel):
    id: str
    name: str
    version: int = 1
    items: list[CollectionItem] = Field(default_factory=list)


class CollectionSummary(BaseModel):
    """Lightweight projection used by the list endpoint."""
    id: str
    name: str
    request_count: int


class CreateCollectionInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class CreateFolderInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_folder_id: str | None = None


class SaveRequestInput(BaseModel):
    id: str | None = None
    name: str = Field(..., min_length=1, max_length=200)
    method: HttpMethod = "GET"
    url: str = Field(..., min_length=1)
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
    parent_folder_id: str | None = None
