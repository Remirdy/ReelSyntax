import json
import os
from typing import Any
import urllib.error
import urllib.request

from .base import enforce_endpoint_network_policy, extract_json_object

DEFAULT_OPENAI_COMPAT_ENDPOINT = "http://127.0.0.1:8000/v1"


class OpenAICompatProvider:
    name = "openai_compat"

    def __init__(
        self,
        *,
        model: str = "",
        endpoint: str = "",
        api_key: str | None = None,
        timeout_sec: int = 60,
        allow_network: bool = False,
    ) -> None:
        self.model = model.strip() or "local-model"
        self.endpoint = (endpoint.strip() or DEFAULT_OPENAI_COMPAT_ENDPOINT).rstrip("/")
        resolved_key = api_key if api_key is not None else (os.environ.get("REELSYNTAX_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or "")
        self._api_key = resolved_key.strip()
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
        url = f"{self.endpoint}/chat/completions"
        enforce_endpoint_network_policy(url, allow_network=self.allow_network)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "reelsyntax_output",
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        if seed is not None:
            payload["seed"] = int(seed)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                raw_body = resp.read(2_097_152).decode("utf-8")
        except urllib.error.HTTPError as error:
            raise ValueError(f"OpenAI-compatible endpoint returned HTTP {error.code}") from error
        except urllib.error.URLError as error:
            raise ValueError(f"OpenAI-compatible endpoint unreachable ({self.endpoint}): {error.reason}") from error
        envelope = json.loads(raw_body)
        choices = envelope.get("choices") or []
        if not choices:
            raise ValueError("OpenAI-compatible endpoint returned no completion choices")
        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, dict):
            return content
        return extract_json_object(str(content))
