from typing import Any

from ...config import ResolvedConfig, load_config
from .base import LLMProvider, enforce_endpoint_network_policy, extract_json_object, is_loopback_endpoint
from .offline_rules import OfflineRulesProvider
from .ollama import OllamaProvider, probe_ollama
from .openai_compat import OpenAICompatProvider


class HostAgentProvider:
    name = "mcp_host"

    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self._responses = list(responses or [])

    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        *,
        seed: int | None = None,
    ) -> dict[str, Any]:
        _ = (system, user, schema, seed)
        if not self._responses:
            raise ValueError("mcp_host provider expects structured plans supplied through MCP gateway tools")
        return self._responses.pop(0)


def create_provider(
    name: str | None = None,
    *,
    model: str | None = None,
    endpoint: str | None = None,
    allow_network: bool | None = None,
    config: ResolvedConfig | None = None,
) -> LLMProvider:
    cfg = config if config is not None else load_config()
    selected = (name or cfg.provider.name).strip()
    net = cfg.general.allow_network if allow_network is None else bool(allow_network)
    chosen_model = cfg.provider.model if model is None else model
    chosen_endpoint = cfg.provider.endpoint if endpoint is None else endpoint
    timeout = cfg.provider.timeout_sec

    if selected == "offline_rules":
        return OfflineRulesProvider()
    if selected == "ollama":
        return OllamaProvider(
            model=chosen_model,
            endpoint=chosen_endpoint,
            timeout_sec=timeout,
            allow_network=net,
        )
    if selected == "openai_compat":
        return OpenAICompatProvider(
            model=chosen_model,
            endpoint=chosen_endpoint,
            timeout_sec=timeout,
            allow_network=net,
        )
    if selected == "mcp_host":
        return HostAgentProvider()
    raise ValueError(f"Unsupported LLM provider: {selected!r}")


def probe_providers(config: ResolvedConfig | None = None) -> dict[str, Any]:
    cfg = config if config is not None else load_config()
    ollama_status = probe_ollama(cfg.provider.endpoint if cfg.provider.name == "ollama" and cfg.provider.endpoint else "http://127.0.0.1:11434")
    return {
        "configured_default": cfg.provider.name,
        "offline_rules": {"available": True, "network_required": False},
        "ollama": ollama_status,
        "openai_compat": {
            "configured_endpoint": cfg.provider.endpoint if cfg.provider.name == "openai_compat" else "",
            "network_opt_in_enabled": cfg.general.allow_network,
        },
        "mcp_host": {"available": True, "mode": "gateway-supplied"},
    }


__all__ = [
    "HostAgentProvider",
    "LLMProvider",
    "OfflineRulesProvider",
    "OllamaProvider",
    "OpenAICompatProvider",
    "create_provider",
    "enforce_endpoint_network_policy",
    "extract_json_object",
    "is_loopback_endpoint",
    "probe_ollama",
    "probe_providers",
]
