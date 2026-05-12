"""Collection docs: generate documentation from a collection."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from theridion_sidecar import storage

router = APIRouter(prefix="/api/docs", tags=["collection-docs"])


class DocsOutput(BaseModel):
    markdown: str = ""
    html: str = ""


def _items_to_md(items: list, depth: int = 0) -> str:
    lines: list[str] = []
    indent = "#" * (depth + 3)
    for item in items:
        d = item.model_dump() if hasattr(item, "model_dump") else item
        if d.get("is_folder"):
            lines.append(f"{indent} {d['name']}\n")
            if d.get("items"):
                lines.append(_items_to_md(d["items"], depth + 1))
        else:
            method = d.get("method", "GET")
            url = d.get("url", "")
            lines.append(f"{indent} {d['name']}\n")
            lines.append(f"**{method}** `{url}`\n")
            if d.get("headers"):
                lines.append("**Headers:**\n")
                for k, v in d["headers"].items():
                    lines.append(f"- `{k}: {v}`\n")
            if d.get("body"):
                lines.append(f"\n```json\n{d['body']}\n```\n")
            lines.append("")
    return "\n".join(lines)


@router.post("/generate/{collection_id}", response_model=DocsOutput)
async def generate_docs(collection_id: str) -> DocsOutput:
    col = storage.load_collection(collection_id)
    if col is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    md = f"# {col.name}\n\n"
    md += _items_to_md(col.items)

    html = f"<h1>{col.name}</h1>\n<pre>{md}</pre>"
    return DocsOutput(markdown=md, html=html)
