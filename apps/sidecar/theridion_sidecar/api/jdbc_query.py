"""JDBC query: execute SQL queries (SQLite supported, others stubbed)."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/jdbc", tags=["jdbc"])


class JdbcInput(BaseModel):
    connection_string: str
    query: str
    params: list = []


class JdbcOutput(BaseModel):
    columns: list[str] = []
    rows: list[list] = []
    row_count: int = 0
    error: str | None = None


@router.post("/query", response_model=JdbcOutput)
async def jdbc_query(body: JdbcInput) -> JdbcOutput:
    cs = body.connection_string.lower()
    if "sqlite" in cs or cs.endswith(".db") or cs.endswith(".sqlite"):
        db_path = body.connection_string.replace("sqlite:///", "").replace("sqlite://", "")
        if not db_path or db_path == ":memory:":
            db_path = ":memory:"
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.execute(body.query, body.params)
            columns = [d[0] for d in cur.description] if cur.description else []
            rows = [list(r) for r in cur.fetchall()]
            conn.close()
            return JdbcOutput(columns=columns, rows=rows, row_count=len(rows))
        except Exception as exc:
            return JdbcOutput(error=str(exc))
    else:
        return JdbcOutput(
            error=f"Unsupported database type in connection string. Only SQLite is currently supported."
        )
