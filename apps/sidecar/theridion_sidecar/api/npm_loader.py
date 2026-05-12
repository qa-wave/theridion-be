"""NPM loader: install and execute npm modules in temp directories."""

from __future__ import annotations

import asyncio
import tempfile

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/scripts", tags=["npm-loader"])


class NpmInstallInput(BaseModel):
    module_name: str


class NpmInstallOutput(BaseModel):
    installed: bool = False
    path: str = ""
    error: str | None = None


class NpmExecuteInput(BaseModel):
    script: str
    modules: list[str] = []


class NpmExecuteOutput(BaseModel):
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1


@router.post("/install-module", response_model=NpmInstallOutput)
async def install_module(body: NpmInstallInput) -> NpmInstallOutput:
    try:
        tmpdir = tempfile.mkdtemp(prefix="theridion_npm_")
        proc = await asyncio.create_subprocess_exec(
            "npm", "install", body.module_name,
            cwd=tmpdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode == 0:
            return NpmInstallOutput(installed=True, path=tmpdir)
        return NpmInstallOutput(installed=False, error=stderr.decode(errors="replace"))
    except Exception as exc:
        return NpmInstallOutput(error=str(exc))


@router.post("/execute-with-modules", response_model=NpmExecuteOutput)
async def execute_with_modules(body: NpmExecuteInput) -> NpmExecuteOutput:
    try:
        tmpdir = tempfile.mkdtemp(prefix="theridion_npm_exec_")
        if body.modules:
            proc = await asyncio.create_subprocess_exec(
                "npm", "install", *body.modules,
                cwd=tmpdir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=30)

        script_path = f"{tmpdir}/script.js"
        with open(script_path, "w") as f:
            f.write(body.script)

        proc = await asyncio.create_subprocess_exec(
            "node", script_path,
            cwd=tmpdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        return NpmExecuteOutput(
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
            exit_code=proc.returncode or 0,
        )
    except Exception as exc:
        return NpmExecuteOutput(stderr=str(exc), exit_code=-1)
