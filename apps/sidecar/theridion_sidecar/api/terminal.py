"""Terminal: execute shell commands with timeout."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/terminal", tags=["terminal"])


class TerminalInput(BaseModel):
    command: str
    cwd: str | None = None


class TerminalOutput(BaseModel):
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1


@router.post("/exec", response_model=TerminalOutput)
async def exec_command(body: TerminalInput) -> TerminalOutput:
    try:
        proc = await asyncio.create_subprocess_shell(
            body.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=body.cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return TerminalOutput(stderr="Command timed out (5s limit)", exit_code=-1)

        return TerminalOutput(
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
            exit_code=proc.returncode or 0,
        )
    except Exception as exc:
        return TerminalOutput(stderr=str(exc), exit_code=-1)
