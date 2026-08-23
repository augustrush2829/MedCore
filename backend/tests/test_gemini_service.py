import json
import urllib.error

import pytest

from app.core.config import get_settings
from app.services import gemini


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class _FakeResponseCM:
    def __init__(self, payload: dict):
        self._response = _FakeResponse(payload)

    def __enter__(self):
        return self._response

    def __exit__(self, *exc):
        return False


def test_generate_json_calls_text_model_and_parses_response(monkeypatch):
    captured: dict = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _FakeResponseCM({"response": json.dumps({"ok": True})})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = gemini.generate_json("Summarize the case", system_instruction="Be terse")

    settings = get_settings()
    assert captured["url"] == f"{settings.ollama_base_url}/api/generate"
    assert captured["body"]["model"] == settings.ollama_model
    assert captured["body"]["system"] == "Be terse"
    assert captured["body"]["format"] == "json"
    assert "images" not in captured["body"]
    assert result == {"ok": True}


def test_generate_json_uses_vision_model_when_image_present(monkeypatch):
    captured: dict = {}

    def fake_urlopen(request, timeout=None):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponseCM({"response": json.dumps({"observations": []})})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    gemini.generate_json(
        "Extract lab rows",
        image={"mime_type": "image/png", "base64": "abc123"},
    )

    settings = get_settings()
    assert captured["body"]["model"] == settings.ollama_vision_model
    assert captured["body"]["images"] == ["abc123"]


def test_generate_json_parses_response_wrapped_in_code_fence(monkeypatch):
    def fake_urlopen(request, timeout=None):
        return _FakeResponseCM({"response": "```json\n{\"a\": 1}\n```"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    assert gemini.generate_json("prompt") == {"a": 1}


def test_generate_json_raises_on_empty_response(monkeypatch):
    def fake_urlopen(request, timeout=None):
        return _FakeResponseCM({"response": ""})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError):
        gemini.generate_json("prompt")


def test_generate_json_raises_clear_error_when_ollama_unreachable(monkeypatch):
    def fake_urlopen(request, timeout=None):
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="Ollama сервертэй холбогдож чадсангүй"):
        gemini.generate_json("prompt")
