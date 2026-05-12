"""Response schema validation — validate JSON against JSON Schema."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/schema", tags=["schema"])


class ValidateInput(BaseModel):
    body: str
    json_schema: str = Field(alias="schema")


class ValidationError(BaseModel):
    path: str
    message: str


class ValidateOutput(BaseModel):
    valid: bool
    errors: list[ValidationError] = Field(default_factory=list)


@router.post("/validate", response_model=ValidateOutput)
def validate_schema(body: ValidateInput) -> ValidateOutput:
    try:
        data = json.loads(body.body)
    except json.JSONDecodeError as e:
        return ValidateOutput(valid=False, errors=[ValidationError(path="$", message=f"Invalid JSON: {e}")])

    try:
        schema = json.loads(body.json_schema)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid schema JSON: {e}") from e

    errors = _validate(data, schema, "$")
    return ValidateOutput(valid=len(errors) == 0, errors=errors)


def _validate(data: Any, schema: dict[str, Any], path: str) -> list[ValidationError]:
    """Simple JSON Schema validator (subset — type, required, properties, items)."""
    errors: list[ValidationError] = []

    # Type check
    expected_type = schema.get("type")
    if expected_type:
        type_map = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "array": list, "object": dict, "null": type(None)}
        expected = type_map.get(expected_type)
        if expected and not isinstance(data, expected):
            errors.append(ValidationError(path=path, message=f"Expected {expected_type}, got {type(data).__name__}"))
            return errors

    # Required
    if isinstance(data, dict):
        for req in schema.get("required", []):
            if req not in data:
                errors.append(ValidationError(path=f"{path}.{req}", message=f"Required field missing"))

    # Properties
    props = schema.get("properties", {})
    if isinstance(data, dict) and props:
        for key, sub_schema in props.items():
            if key in data:
                errors.extend(_validate(data[key], sub_schema, f"{path}.{key}"))

    # Items
    items_schema = schema.get("items")
    if isinstance(data, list) and items_schema:
        for i, item in enumerate(data[:50]):  # limit to 50
            errors.extend(_validate(item, items_schema, f"{path}[{i}]"))

    # Enum
    enum_vals = schema.get("enum")
    if enum_vals and data not in enum_vals:
        errors.append(ValidationError(path=path, message=f"Value {data!r} not in enum {enum_vals}"))

    # MinLength / MaxLength
    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append(ValidationError(path=path, message=f"String too short (min {schema['minLength']})"))
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            errors.append(ValidationError(path=path, message=f"String too long (max {schema['maxLength']})"))

    # Minimum / Maximum
    if isinstance(data, (int, float)):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(ValidationError(path=path, message=f"Value {data} below minimum {schema['minimum']}"))
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(ValidationError(path=path, message=f"Value {data} above maximum {schema['maximum']}"))

    return errors
