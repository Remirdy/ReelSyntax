import ipaddress
import json
import re
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlparse


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        *,
        seed: int | None = None,
    ) -> dict[str, Any]: ...


FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def extract_json_object(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if not text:
        raise ValueError("Provider returned an empty response")
    fenced = FENCED_JSON_RE.search(text)
    candidate = fenced.group(1).strip() if fenced else text
    if not candidate.startswith("{"):
        first = candidate.find("{")
        last = candidate.rfind("}")
        if first != -1 and last > first:
            candidate = candidate[first:last + 1]
    cleaned = TRAILING_COMMA_RE.sub(r"\1", candidate)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ValueError(f"Provider output is not valid JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise ValueError("Provider output must be a JSON object")
    return parsed


def is_loopback_endpoint(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"Unsupported provider endpoint URL: {url!r}")
    host = parsed.hostname.lower()
    if host == "localhost":
        return True
    try:
        addr = ipaddress.ip_address(host)
        return addr.is_loopback
    except ValueError:
        return False


def enforce_endpoint_network_policy(url: str, *, allow_network: bool) -> None:
    if is_loopback_endpoint(url):
        return
    if not allow_network:
        raise ValueError(
            f"Remote LLM endpoint {url!r} requires explicit network opt-in (--allow-network or general.allow_network = true)"
        )
