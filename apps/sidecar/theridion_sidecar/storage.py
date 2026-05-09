"""File-based persistence for collections and requests.

Storage layout::

    $THERIDION_HOME/                 (default: ~/.theridion)
    └── collections/
        ├── <collection-uuid>.json
        └── <collection-uuid>.json

Each collection file is a single JSON document with a flat list of
saved requests — folder hierarchy and `.bru` interop come later. Writes
are atomic (write-temp-then-rename) so a crash mid-save cannot corrupt
an existing file.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from .models import Collection, CollectionSummary, SavedRequest


SCHEMA_VERSION = 1


def home_dir() -> Path:
    """Resolve the storage root, honoring THERIDION_HOME for tests."""
    override = os.environ.get("THERIDION_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".theridion"


def collections_dir() -> Path:
    d = home_dir() / "collections"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path_for(collection_id: str) -> Path:
    # Collection IDs are UUIDs the server generates, so they're already
    # filesystem-safe; we still validate to keep paths predictable.
    safe = uuid.UUID(collection_id)  # raises ValueError if malformed
    return collections_dir() / f"{safe}.json"


def list_summaries() -> list[CollectionSummary]:
    out: list[CollectionSummary] = []
    for p in sorted(collections_dir().glob("*.json")):
        try:
            data = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            # A broken file shouldn't take the whole list down. We keep going
            # and surface the error in a future "diagnostics" endpoint.
            continue
        out.append(
            CollectionSummary(
                id=data["id"],
                name=data.get("name", "Untitled"),
                request_count=len(data.get("items", [])),
            )
        )
    return out


def get(collection_id: str) -> Collection | None:
    p = _path_for(collection_id)
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    return Collection(**data)


def create(name: str) -> Collection:
    coll = Collection(
        id=str(uuid.uuid4()),
        name=name,
        version=SCHEMA_VERSION,
        items=[],
    )
    _atomic_write(coll)
    return coll


def add_request(collection_id: str, req: SavedRequest) -> Collection:
    coll = get(collection_id)
    if coll is None:
        raise FileNotFoundError(f"collection {collection_id} not found")
    # If a request with the same id exists, replace it; otherwise append.
    existing_idx = next(
        (i for i, r in enumerate(coll.items) if r.id == req.id), None
    )
    if existing_idx is None:
        coll.items.append(req)
    else:
        coll.items[existing_idx] = req
    _atomic_write(coll)
    return coll


def delete_request(collection_id: str, request_id: str) -> Collection:
    coll = get(collection_id)
    if coll is None:
        raise FileNotFoundError(f"collection {collection_id} not found")
    coll.items = [r for r in coll.items if r.id != request_id]
    _atomic_write(coll)
    return coll


def delete_collection(collection_id: str) -> bool:
    p = _path_for(collection_id)
    if not p.exists():
        return False
    p.unlink()
    return True


def _atomic_write(coll: Collection) -> None:
    p = _path_for(coll.id)
    payload: dict[str, Any] = coll.model_dump(mode="json")
    payload["version"] = SCHEMA_VERSION
    # Write to a sibling tempfile, fsync, then atomically replace.
    fd, tmp_path_str = tempfile.mkstemp(
        prefix=f"{coll.id}.", suffix=".json.tmp", dir=str(p.parent)
    )
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, p)
    except Exception:
        # Best-effort cleanup of the orphaned tempfile.
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
