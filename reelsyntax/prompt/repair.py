import json
from typing import Any, Callable

from .providers.base import LLMProvider


class PromptRepairExhaustedError(ValueError):
    def __init__(self, attempts: int, errors: list[str]) -> None:
        self.attempts = attempts
        self.errors = list(errors)
        last = errors[-1] if errors else "validation failed"
        super().__init__(
            f"Structured output failed schema validation after {attempts} attempts; last error: {last}"
        )


def validate_against_minimal_schema(data: Any, schema: dict[str, Any], path: str = "output") -> None:
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(data, dict):
            raise ValueError(f"{path}: expected JSON object")
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for req in required:
            if req not in data:
                raise ValueError(f"{path}.{req}: missing required field")
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(data) - set(props))
            if unknown:
                raise ValueError(f"{path}: unexpected fields {unknown}")
        for key, value in data.items():
            if key in props:
                validate_against_minimal_schema(value, props[key], f"{path}.{key}")
        return
    if expected_type == "array":
        if not isinstance(data, list):
            raise ValueError(f"{path}: expected array")
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if min_items is not None and len(data) < int(min_items):
            raise ValueError(f"{path}: expected at least {min_items} items")
        if max_items is not None and len(data) > int(max_items):
            raise ValueError(f"{path}: expected at most {max_items} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(data):
                validate_against_minimal_schema(item, item_schema, f"{path}[{idx}]")
        return
    if expected_type == "string":
        if not isinstance(data, str):
            raise ValueError(f"{path}: expected string")
        max_len = schema.get("maxLength")
        if max_len is not None and len(data) > int(max_len):
            raise ValueError(f"{path}: string exceeds maxLength {max_len}")
        enum_vals = schema.get("enum")
        if enum_vals is not None and data not in enum_vals:
            raise ValueError(f"{path}: value {data!r} must be one of {enum_vals}")
        return
    if expected_type == "integer":
        if type(data) is not int:
            raise ValueError(f"{path}: expected integer")
        low = schema.get("minimum")
        high = schema.get("maximum")
        if low is not None and data < int(low):
            raise ValueError(f"{path}: integer {data} < minimum {low}")
        if high is not None and data > int(high):
            raise ValueError(f"{path}: integer {data} > maximum {high}")
        return
    if expected_type == "boolean":
        if type(data) is not bool:
            raise ValueError(f"{path}: expected boolean")


def generate_with_repair(
    provider: LLMProvider,
    *,
    system: str,
    user: str,
    schema: dict[str, Any],
    validator: Callable[[dict[str, Any]], Any] | None = None,
    seed: int | None = None,
    max_attempts: int = 3,
) -> tuple[dict[str, Any], int]:
    if max_attempts < 1 or max_attempts > 4:
        raise ValueError("max_attempts must be between 1 and 4")
    errors: list[str] = []
    current_user = user

    for attempt in range(1, max_attempts + 1):
        attempt_seed = None if seed is None else seed + (attempt - 1)
        try:
            candidate = provider.generate_json(system, current_user, schema, seed=attempt_seed)
            if not isinstance(candidate, dict):
                raise ValueError("Provider did not return a JSON object")
            validate_against_minimal_schema(candidate, schema)
            if validator is not None:
                validator(candidate)
            return candidate, attempt
        except ValueError as error:
            err_msg = str(error)
            errors.append(err_msg)
            if attempt >= max_attempts:
                break
            current_user = (
                f"{user}\n\n"
                f"Previous attempt #{attempt} failed validation with error:\n"
                f"{err_msg}\n"
                f"Return ONLY a corrected JSON object matching this schema:\n"
                f"{json.dumps(schema, ensure_ascii=False)}"
            )

    raise PromptRepairExhaustedError(max_attempts, errors)
