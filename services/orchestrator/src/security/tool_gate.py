from pydantic import BaseModel, ValidationError


def classify_tool_error_reason(status: int | None, exc: Exception | None) -> str:
    if exc and "timeout" in str(exc).lower():
        return "timeout"
    if status == 429:
        return "429"
    if status and 500 <= status <= 599:
        return "5xx"
    if exc and "schema" in str(exc).lower():
        return "schema"
    return "other"


def validate_json_schema(model: type[BaseModel], args: dict):
    try:
        model(**args)
    except ValidationError as e:
        raise ValueError(f"schema: {e}") from e


def gate_tool_call(
    tool_name: str,
    args: dict,
    mode: str,
    policy: dict,
    model: type[BaseModel] | None = None,
):
    if model:
        validate_json_schema(model, args)  # raisar vid schemafel
    allowed = set(policy.get("modes", {}).get(mode, {}).get("tools_allowed", []))
    if tool_name not in allowed:
        raise PermissionError("tool_not_allowed")
    return True
