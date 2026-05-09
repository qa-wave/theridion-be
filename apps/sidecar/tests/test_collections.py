"""Integration tests for collections CRUD against the live FastAPI app.

Each test gets a temporary THERIDION_HOME so they're hermetic — there's
no shared state between tests and no contamination of the user's real
home directory.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("THERIDION_HOME", str(tmp_path))
    # Import inside the fixture so the env var is already set when the
    # storage module is first imported.
    from theridion_sidecar.main import create_app

    return TestClient(create_app())


def test_list_is_empty_initially(client: TestClient) -> None:
    res = client.get("/api/collections")
    assert res.status_code == 200
    assert res.json() == []


def test_create_then_list_roundtrip(client: TestClient) -> None:
    res = client.post("/api/collections", json={"name": "Smoke"})
    assert res.status_code == 201
    coll = res.json()
    assert coll["name"] == "Smoke"
    assert coll["items"] == []

    listed = client.get("/api/collections").json()
    assert len(listed) == 1
    assert listed[0]["id"] == coll["id"]
    assert listed[0]["request_count"] == 0


def test_save_request_appends_then_replaces(client: TestClient) -> None:
    coll = client.post("/api/collections", json={"name": "Repo"}).json()
    cid = coll["id"]

    r1 = client.post(
        f"/api/collections/{cid}/requests",
        json={"name": "Get", "method": "GET", "url": "https://example.com"},
    ).json()
    assert len(r1["items"]) == 1
    rid = r1["items"][0]["id"]

    # Same id → replace, not append.
    r2 = client.post(
        f"/api/collections/{cid}/requests",
        json={"id": rid, "name": "Get (renamed)", "method": "GET", "url": "https://example.com/v2"},
    ).json()
    assert len(r2["items"]) == 1
    assert r2["items"][0]["name"] == "Get (renamed)"
    assert r2["items"][0]["url"] == "https://example.com/v2"

    # Different id → append.
    r3 = client.post(
        f"/api/collections/{cid}/requests",
        json={"name": "Post", "method": "POST", "url": "https://example.com"},
    ).json()
    assert len(r3["items"]) == 2


def test_delete_request_removes_only_that_one(client: TestClient) -> None:
    coll = client.post("/api/collections", json={"name": "C"}).json()
    cid = coll["id"]
    a = client.post(
        f"/api/collections/{cid}/requests",
        json={"name": "A", "url": "https://a.example"},
    ).json()
    b = client.post(
        f"/api/collections/{cid}/requests",
        json={"name": "B", "url": "https://b.example"},
    ).json()
    assert len(b["items"]) == 2

    rid_a = a["items"][0]["id"]
    after_del = client.delete(f"/api/collections/{cid}/requests/{rid_a}").json()
    assert [r["name"] for r in after_del["items"]] == ["B"]


def test_delete_collection_removes_file(client: TestClient, tmp_path: Path) -> None:
    coll = client.post("/api/collections", json={"name": "Doomed"}).json()
    cid = coll["id"]
    file_path = tmp_path / "collections" / f"{cid}.json"
    assert file_path.exists()

    res = client.delete(f"/api/collections/{cid}")
    assert res.status_code == 204
    assert not file_path.exists()


def test_get_unknown_collection_404s(client: TestClient) -> None:
    res = client.get("/api/collections/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


def test_atomic_write_does_not_leave_temp_files(client: TestClient, tmp_path: Path) -> None:
    coll = client.post("/api/collections", json={"name": "Atomic"}).json()
    cid = coll["id"]
    client.post(
        f"/api/collections/{cid}/requests",
        json={"name": "X", "url": "https://example.com"},
    )
    leftover = list((tmp_path / "collections").glob("*.tmp"))
    assert leftover == [], f"unexpected temp files: {leftover}"


def test_storage_root_respects_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THERIDION_HOME", str(tmp_path / "x"))
    from theridion_sidecar import storage

    # Re-resolve since tests use monkeypatch, not module-level constants.
    assert storage.home_dir() == (tmp_path / "x").resolve()
    assert os.path.isdir(storage.collections_dir())
