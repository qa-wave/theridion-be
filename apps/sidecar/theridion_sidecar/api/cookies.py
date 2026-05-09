"""Cookie jar API — view and clear cookies per environment."""

from __future__ import annotations

from fastapi import APIRouter

from .. import cookies

router = APIRouter(prefix="/api/cookies", tags=["cookies"])


@router.get("/{env_id}", response_model=cookies.CookieJar)
def get_cookies(env_id: str) -> cookies.CookieJar:
    return cookies.load(env_id)


@router.delete("/{env_id}", status_code=204)
def clear_cookies(env_id: str) -> None:
    cookies.clear(env_id)
