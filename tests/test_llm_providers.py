import io
import json
import unittest
from unittest.mock import patch

from reelsyntax.prompt import (
    HostAgentProvider,
    LLMProvider,
    OfflineRulesProvider,
    OllamaProvider,
    OpenAICompatProvider,
    create_provider,
    extract_json_object,
)
from reelsyntax.prompt.providers.base import enforce_endpoint_network_policy, is_loopback_endpoint

SAMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "language": {"type": "string"},
        "aspect": {"type": "string"},
        "heading": {"type": "string"},
        "background": {"type": "string"},
        "foreground": {"type": "string"},
        "accent": {"type": "string"},
        "beats": {
            "type": "array",
            "minItems": 3,
            "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "heading": {"type": "string"},
                    "subheading": {"type": "string"},
                    "duration_frames": {"type": "integer", "minimum": 30, "maximum": 180},
                },
                "required": ["id", "heading", "subheading", "duration_frames"],
            },
        },
    },
    "required": ["language", "aspect", "heading", "background", "foreground", "accent", "beats"],
}


class _FakeHttpResponse:
    def __init__(self, body: dict) -> None:
        self._stream = io.BytesIO(json.dumps(body).encode("utf-8"))

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def __enter__(self) -> "_FakeHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class LLMProviderTests(unittest.TestCase):
    def test_offline_rules_provider_is_deterministic_and_multilingual(self) -> None:
        provider = OfflineRulesProvider()
        self.assertIsInstance(provider, LLMProvider)
        first = provider.generate_json(
            "Plan beats",
            "5 odaklanma ipucu, 9:16, sakin renkler",
            SAMPLE_SCHEMA,
            seed=42,
        )
        second = provider.generate_json(
            "Plan beats",
            "5 odaklanma ipucu, 9:16, sakin renkler",
            SAMPLE_SCHEMA,
            seed=42,
        )
        self.assertEqual(first, second)
        self.assertEqual(first["language"], "tr")
        self.assertEqual(first["aspect"], "9:16")
        self.assertEqual(len(first["beats"]), 3)

        de_out = provider.generate_json(
            "Plan beats",
            "Kurzes Video ohne Musik mit ruhigen Farben und Untertiteln",
            SAMPLE_SCHEMA,
            seed=7,
        )
        self.assertEqual(de_out["language"], "de")

    def test_extract_json_handles_fenced_blocks_and_trailing_commas(self) -> None:
        fenced = 'Sure:\n```json\n{"heading": "FOCUS", "items": [1, 2,],}\n```\n'
        self.assertEqual(extract_json_object(fenced), {"heading": "FOCUS", "items": [1, 2]})
        with self.assertRaises(ValueError):
            extract_json_object("not json at all")

    def test_loopback_vs_remote_endpoint_network_policy(self) -> None:
        self.assertTrue(is_loopback_endpoint("http://127.0.0.1:11434/api/chat"))
        self.assertTrue(is_loopback_endpoint("http://localhost:8000/v1/chat/completions"))
        self.assertFalse(is_loopback_endpoint("https://api.example.com/v1/chat/completions"))

        enforce_endpoint_network_policy("http://127.0.0.1:11434/api/chat", allow_network=False)
        with self.assertRaisesRegex(ValueError, "allow-network"):
            enforce_endpoint_network_policy("https://api.example.com/v1/chat/completions", allow_network=False)
        enforce_endpoint_network_policy("https://api.example.com/v1/chat/completions", allow_network=True)

    def test_ollama_and_openai_compat_providers_with_mocked_transport(self) -> None:
        ollama = OllamaProvider(model="local-test", endpoint="http://127.0.0.1:11434", allow_network=False)
        fake_ollama_payload = {"message": {"content": '{"ok": true, "scene_count": 3}'}}
        with patch("urllib.request.urlopen", return_value=_FakeHttpResponse(fake_ollama_payload)) as mocked:
            out = ollama.generate_json("sys", "usr", {"type": "object"}, seed=99)
        self.assertEqual(out, {"ok": True, "scene_count": 3})
        sent_req = mocked.call_args[0][0]
        sent_body = json.loads(sent_req.data.decode("utf-8"))
        self.assertEqual(sent_body["options"]["seed"], 99)

        remote_openai = OpenAICompatProvider(
            model="remote-test",
            endpoint="https://api.example.com/v1",
            api_key="test-key-never-logged",
            allow_network=False,
        )
        with self.assertRaisesRegex(ValueError, "allow-network"):
            remote_openai.generate_json("sys", "usr", {"type": "object"})

        opted_in = OpenAICompatProvider(
            model="remote-test",
            endpoint="https://api.example.com/v1",
            api_key="test-key-never-logged",
            allow_network=True,
        )
        fake_oai_payload = {"choices": [{"message": {"content": "```json\n{\"title\": \"CLEAN\"}\n```"}}]}
        with patch("urllib.request.urlopen", return_value=_FakeHttpResponse(fake_oai_payload)) as oai_mock:
            res = opted_in.generate_json("sys", "usr", {"type": "object"}, seed=12)
        self.assertEqual(res, {"title": "CLEAN"})
        self.assertIn("Authorization", oai_mock.call_args[0][0].headers)

    def test_host_agent_and_factory_selection(self) -> None:
        host = HostAgentProvider([{"step": "idea"}])
        self.assertEqual(host.generate_json("s", "u", {}), {"step": "idea"})
        with self.assertRaises(ValueError):
            host.generate_json("s", "u", {})
        created = create_provider("offline_rules")
        self.assertEqual(created.name, "offline_rules")


if __name__ == "__main__":
    unittest.main()
