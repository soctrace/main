from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from app.ask.llm.errors import LLMProviderError
from app.ask.llm.schemas import LLMToolCall, LLMToolSchema


SAFE_TOOL_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$")
ALLOWED_SCHEMA_KEYS = {
    "type",
    "description",
    "properties",
    "required",
    "items",
    "enum",
    "minimum",
    "maximum",
    "default",
    "format",
}
MAX_SCHEMA_BYTES = 64_000


class GeminiSchemaAdapterError(LLMProviderError):
    """Raised when a generic LLM tool schema cannot be adapted safely for Gemini."""


def normalize_json_schema_for_gemini(schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(schema, dict):
        raise GeminiSchemaAdapterError("Tool parameters must be a JSON schema object.")

    source = deepcopy(schema)
    definitions = {}
    definitions.update(source.get("$defs") or {})
    definitions.update(source.get("definitions") or {})
    normalized = _normalize_schema_node(source, definitions)

    if normalized.get("type") != "object":
        raise GeminiSchemaAdapterError("Top-level tool parameters must be an object schema.")
    normalized.setdefault("properties", {})
    if not isinstance(normalized["properties"], dict):
        raise GeminiSchemaAdapterError("Tool parameters.properties must be an object.")
    normalized["required"] = [
        field
        for field in normalized.get("required", [])
        if field in normalized["properties"]
    ]
    return normalized


def sanitize_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    return normalize_json_schema_for_gemini(schema)


def _normalize_schema_node(node: Any, definitions: dict[str, Any]) -> Any:
    if isinstance(node, list):
        return [_normalize_schema_node(item, definitions) for item in node]
    if not isinstance(node, dict):
        return node

    if "$ref" in node:
        ref = str(node["$ref"])
        if not ref.startswith("#/$defs/") and not ref.startswith("#/definitions/"):
            raise GeminiSchemaAdapterError(f"Unsupported JSON schema reference: {ref}")
        ref_name = ref.split("/")[-1]
        if ref_name not in definitions:
            raise GeminiSchemaAdapterError(f"Unresolved JSON schema reference: {ref}")
        return _normalize_schema_node(definitions[ref_name], definitions)

    if "anyOf" in node:
        return _normalize_nullable_union(node, "anyOf", definitions)
    if "oneOf" in node:
        return _normalize_nullable_union(node, "oneOf", definitions)
    if "allOf" in node:
        all_of = node.get("allOf") or []
        if len(all_of) != 1:
            raise GeminiSchemaAdapterError("Cannot safely normalize allOf with multiple schemas.")
        merged = {**node, **all_of[0]}
        merged.pop("allOf", None)
        return _normalize_schema_node(merged, definitions)

    normalized: dict[str, Any] = {}
    for key, value in node.items():
        if key in {"title", "$defs", "definitions", "examples", "additionalProperties"}:
            continue
        if key not in ALLOWED_SCHEMA_KEYS:
            continue
        if key == "properties":
            if not isinstance(value, dict):
                raise GeminiSchemaAdapterError("properties must be an object.")
            normalized[key] = {
                property_name: _normalize_schema_node(property_schema, definitions)
                for property_name, property_schema in value.items()
                if isinstance(property_schema, dict)
            }
            continue
        if key == "items":
            if not isinstance(value, dict):
                raise GeminiSchemaAdapterError("array items must be an object schema.")
            normalized[key] = _normalize_schema_node(value, definitions)
            continue
        if key == "enum":
            if not isinstance(value, list) or not all(isinstance(item, (str, int, float)) for item in value):
                raise GeminiSchemaAdapterError("enum values must be strings or numbers.")
            normalized[key] = value
            continue
        normalized[key] = _normalize_schema_node(value, definitions)

    schema_type = normalized.get("type")
    if schema_type == "object":
        normalized.setdefault("properties", {})
        normalized["required"] = [
            field
            for field in normalized.get("required", [])
            if field in normalized["properties"]
        ]
    if schema_type == "array":
        normalized.setdefault("items", {"type": "string"})
    return normalized


def _normalize_nullable_union(node: dict[str, Any], union_key: str, definitions: dict[str, Any]) -> dict[str, Any]:
    options = node.get(union_key) or []
    non_null = [
        option
        for option in options
        if not (isinstance(option, dict) and option.get("type") == "null")
    ]
    if len(non_null) != 1:
        raise GeminiSchemaAdapterError(f"Cannot safely normalize {union_key} with multiple non-null schemas.")
    merged = {key: value for key, value in node.items() if key != union_key}
    merged.update(non_null[0])
    return _normalize_schema_node(merged, definitions)


def validate_llm_tool_schema(schema: LLMToolSchema) -> None:
    if not schema.name or not SAFE_TOOL_NAME_RE.match(schema.name):
        raise GeminiSchemaAdapterError(f"Invalid tool name: {schema.name!r}")
    if not schema.description or not schema.description.strip():
        raise GeminiSchemaAdapterError(f"Tool {schema.name} must have a description.")
    normalized = normalize_json_schema_for_gemini(schema.parameters)
    unsupported = set(normalized) - ALLOWED_SCHEMA_KEYS
    if unsupported:
        raise GeminiSchemaAdapterError(f"Unsupported top-level schema keys for {schema.name}: {sorted(unsupported)}")
    for required_field in normalized.get("required", []):
        if required_field not in normalized.get("properties", {}):
            raise GeminiSchemaAdapterError(f"Required field {required_field} missing from properties in {schema.name}.")
    encoded = json.dumps(normalized, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > MAX_SCHEMA_BYTES:
        raise GeminiSchemaAdapterError(f"Schema for {schema.name} is too large.")


def to_gemini_function_declaration(tool: LLMToolSchema) -> Any:
    validate_llm_tool_schema(tool)
    parameters = normalize_json_schema_for_gemini(tool.parameters)
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": parameters,
    }


def to_gemini_tools(tools: list[LLMToolSchema]) -> list[Any]:
    if not tools:
        return []

    declarations = [to_gemini_function_declaration(tool) for tool in tools]
    return [{"function_declarations": declarations}]


def parse_gemini_function_call(part: Any) -> LLMToolCall | None:
    function_call = _find_function_call(part)
    if function_call is None:
        return None

    name = getattr(function_call, "name", None)
    args = getattr(function_call, "args", None)
    if isinstance(function_call, dict):
        name = function_call.get("name")
        args = function_call.get("args")
    if not name:
        raise GeminiSchemaAdapterError("Gemini function call is missing a name.")

    arguments = _coerce_args(args)
    return LLMToolCall(
        tool_name=str(name),
        arguments=arguments,
        raw=_object_to_dict(function_call),
    )


def _find_function_call(value: Any) -> Any | None:
    if value is None:
        return None
    if isinstance(value, dict):
        if value.get("function_call") is not None:
            return value["function_call"]
        if value.get("name") and "args" in value:
            return value
        for key in ("parts", "candidates", "function_calls"):
            items = value.get(key) or []
            if key == "candidates":
                items = [item.get("content", item) if isinstance(item, dict) else getattr(item, "content", item) for item in items]
            for item in items:
                found = _find_function_call(item)
                if found is not None:
                    return found
        return None

    function_calls = getattr(value, "function_calls", None)
    if function_calls:
        return function_calls[0]
    if getattr(value, "name", None) and hasattr(value, "args"):
        return value
    direct = getattr(value, "function_call", None)
    if direct is not None:
        return direct
    candidates = getattr(value, "candidates", None) or []
    for candidate in candidates:
        found = _find_function_call(getattr(candidate, "content", candidate))
        if found is not None:
            return found
    parts = getattr(value, "parts", None) or []
    for part in parts:
        found = _find_function_call(part)
        if found is not None:
            return found
    return None


def _coerce_args(args: Any) -> dict[str, Any]:
    if args is None:
        return {}
    if isinstance(args, dict):
        return dict(args)
    if hasattr(args, "items"):
        return dict(args.items())
    for method_name in ("model_dump", "to_json_dict"):
        method = getattr(args, method_name, None)
        if callable(method):
            value = method()
            if isinstance(value, dict):
                return value
    raise GeminiSchemaAdapterError("Gemini function call args are not object-like.")


def _object_to_dict(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {key: _object_to_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_object_to_dict(item) for item in value]
    for method_name in ("model_dump", "to_json_dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                return method()
            except Exception:
                pass
    return {"repr": repr(value)}
