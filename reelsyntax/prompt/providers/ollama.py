import json
from typing import Any
import urllib.error
import urllib.request

from .base import enforce_endpoint_network_policy, extract_json_object

DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"


class OllamaProvider:
    name = "ollama"

    def __init__(
        self,
        *,
        model: str = "",
        endpoint: str = "",
        timeout_sec: int = 60,
        allow_network: bool = False,
    ) -> None:
        self.model = model.strip() or DEFAULT_OLLAMA_MODEL
        self.endpoint = (endpoint.strip() or DEFAULT_OLLAMA_ENDPOINT).rstrip("/")
        self.timeout_sec = max(1, min(600, int(timeout_sec)))
        self.allow_network = bool(allow_network)

    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        *,
        seed: int | None = None,
    ) -> dict[str, Any]:
        url = f"{self.endpoint}/api/chat"
        enforce_endpoint_network_policy(url, allow_network=self.allow_network)
        options: dict[str, Any] = {"temperature": 0}
        if seed is not None:
            options["seed"] = int(seed)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": schema,
            "stream": False,
            "options": options,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                raw_body = resp.read(2_097_152).decode("utf-8")
        except urllib.error.URLError as error:
            raise ValueError(f"Ollama request failed ({self.endpoint}): {error.reason}") from error
        envelope = json.loads(raw_body)
        content = envelope.get("message", {}).get("content", "")
        if isinstance(content, dict):
            return content
        return extract_json_object(str(content))


def probe_ollama(endpoint: str = DEFAULT_OLLAMA_ENDPOINT, timeout_sec: float = 2.0) -> dict[str, Any]:
    base = (endpoint.strip() or DEFAULT_OLLAMA_ENDPOINT).rstrip("/")
    url = f"{base}/api/tags"
    try:
        enforce_endpoint_network_policy(url, allow_network=False)
    except ValueError as error:
        return {"available": False, "endpoint": base, "models": [], "diagnostic": str(error)}
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read(524_288).decode("utf-8"))
        models = [str(m.get("name", "")) for m in data.get("models", []) if m.get("name")]
        return {"available": True, "endpoint": base, "models": models}
    except (OSError, ValueError, urllib.error.URLError) as error:
        return {"available": False, "endpoint": base, "models": [], "diagnostic": str(error)}
