"""MCP server: expose Theridion capabilities as MCP-compatible tools."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class McpTool(BaseModel):
    name: str
    description: str
    input_schema: dict = {}


class McpManifest(BaseModel):
    name: str = "theridion"
    version: str = "0.1.0"
    tools: list[McpTool] = []


class McpInvokeInput(BaseModel):
    tool: str
    arguments: dict = {}


class McpInvokeOutput(BaseModel):
    result: dict = {}
    error: str | None = None


_TOOLS = [
    McpTool(name="execute_request", description="Execute an HTTP request", input_schema={"type": "object", "properties": {"method": {"type": "string"}, "url": {"type": "string"}}}),
    McpTool(name="list_collections", description="List all collections", input_schema={"type": "object"}),
    McpTool(name="list_environments", description="List all environments", input_schema={"type": "object"}),
    McpTool(name="health_check", description="Check sidecar health", input_schema={"type": "object"}),
    McpTool(name="inspect_wsdl", description="Inspect a WSDL document", input_schema={"type": "object", "properties": {"wsdl_url": {"type": "string"}}}),
]


@router.get("/manifest", response_model=McpManifest)
async def get_manifest() -> McpManifest:
    return McpManifest(tools=_TOOLS)


@router.post("/invoke", response_model=McpInvokeOutput)
async def invoke_tool(body: McpInvokeInput) -> McpInvokeOutput:
    tool_names = {t.name for t in _TOOLS}
    if body.tool not in tool_names:
        return McpInvokeOutput(error=f"Unknown tool: {body.tool}")
    return McpInvokeOutput(result={"tool": body.tool, "status": "invoked", "arguments": body.arguments})
