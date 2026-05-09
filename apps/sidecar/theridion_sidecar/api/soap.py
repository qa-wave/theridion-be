"""SOAP-over-HTTP endpoints (inspect a WSDL, execute an operation)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import soap

router = APIRouter(prefix="/api/soap", tags=["soap"])


class InspectInput(BaseModel):
    wsdl_url: str = Field(..., min_length=1)


class ExecuteInput(BaseModel):
    wsdl_url: str = Field(..., min_length=1)
    operation: str = Field(..., min_length=1)
    args: dict[str, Any] = Field(default_factory=dict)


class ExecuteOutput(BaseModel):
    ok: bool
    result: Any = None
    fault: str | None = None


@router.post("/inspect", response_model=soap.WsdlSummary)
def inspect(body: InspectInput) -> soap.WsdlSummary:
    try:
        return soap.inspect_wsdl(body.wsdl_url)
    except Exception as e:
        # zeep raises a variety of XMLParseError, HTTPError, etc.; we
        # collapse them to 400 with the message preserved so the desktop
        # can show what went wrong.
        raise HTTPException(status_code=400, detail=f"WSDL error: {e}") from e


@router.post("/execute", response_model=ExecuteOutput)
def execute(body: ExecuteInput) -> ExecuteOutput:
    try:
        result = soap.execute_operation(body.wsdl_url, body.operation, body.args)
        return ExecuteOutput(ok=True, result=result)
    except ValueError as e:
        # operation not found
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        # SOAP fault, transport error, schema mismatch — surface as a 200
        # ExecuteOutput with `ok=false` so the UI can render the fault
        # detail next to the inputs without falling out of "happy path".
        return ExecuteOutput(ok=False, fault=str(e))
