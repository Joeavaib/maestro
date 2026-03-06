import json

from maestro.llm.ollama_client import OllamaClient


class _Resp:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps({"response": "ok"}).encode("utf-8")


def test_ollama_client_uses_configured_timeout(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout):
        captured["timeout"] = timeout
        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = OllamaClient("http://localhost:11434", timeout_s=321)
    out = client.generate("model", "prompt")

    assert out == "ok"
    assert captured["timeout"] == 321
