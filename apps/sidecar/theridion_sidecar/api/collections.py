"""CRUD endpoints for collections, folders, and the requests inside."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from .. import storage
from ..models import (
    Collection,
    CollectionItem,
    CollectionSummary,
    CreateCollectionInput,
    CreateFolderInput,
    SaveRequestInput,
)

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.get("", response_model=list[CollectionSummary])
def list_collections() -> list[CollectionSummary]:
    return storage.list_summaries()


@router.post("", response_model=Collection, status_code=201)
def create_collection(body: CreateCollectionInput) -> Collection:
    return storage.create(name=body.name)


@router.get("/{collection_id}", response_model=Collection)
def get_collection(collection_id: str) -> Collection:
    coll = storage.get(collection_id)
    if coll is None:
        raise HTTPException(status_code=404, detail="collection not found")
    return coll


@router.delete("/{collection_id}", status_code=204)
def delete_collection(collection_id: str) -> None:
    if not storage.delete_collection(collection_id):
        raise HTTPException(status_code=404, detail="collection not found")


@router.post("/{collection_id}/folders", response_model=Collection, status_code=201)
def create_folder(collection_id: str, body: CreateFolderInput) -> Collection:
    folder = CollectionItem(
        id=str(uuid.uuid4()),
        name=body.name,
        is_folder=True,
        items=[],
    )
    try:
        return storage.add_folder(collection_id, folder, body.parent_folder_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/{collection_id}/folders/{folder_id}", response_model=Collection
)
def delete_folder(collection_id: str, folder_id: str) -> Collection:
    try:
        return storage.delete_folder(collection_id, folder_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{collection_id}/requests", response_model=Collection)
def save_request(collection_id: str, body: SaveRequestInput) -> Collection:
    req = CollectionItem(
        id=body.id or str(uuid.uuid4()),
        name=body.name,
        is_folder=False,
        method=body.method,
        url=body.url,
        headers=body.headers,
        body=body.body,
    )
    try:
        return storage.add_request(collection_id, req, body.parent_folder_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/{collection_id}/requests/{request_id}", response_model=Collection
)
def delete_request(collection_id: str, request_id: str) -> Collection:
    try:
        return storage.delete_request(collection_id, request_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
