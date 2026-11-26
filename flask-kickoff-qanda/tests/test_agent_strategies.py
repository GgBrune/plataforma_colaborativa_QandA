"""Pruebas de las estrategias LLM del issue #12."""

import json
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from qanda.services.agent_service import (
    GeminiStrategy,
    LocalModelStrategy,
    OpenAIStrategy,
)


class FakeResponse:
    """Respuesta HTTP falsa para no llamar a proveedores reales."""

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.body).encode()


def _headers(request):
    return {name.lower(): value for name, value in request.header_items()}


def test_openai_strategy_devuelve_texto_generado():
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = _headers(request)
        return FakeResponse(
            {"choices": [{"message": {"content": "respuesta OpenAI"}}]}
        )

    with patch("qanda.services.agent_service.urlopen", fake_urlopen):
        result = OpenAIStrategy(api_key="clave-openai").generate("prompt de prueba")

    assert result == "respuesta OpenAI"
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer clave-openai"


def test_gemini_strategy_devuelve_texto_generado():
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = _headers(request)
        return FakeResponse(
            {"candidates": [{"content": {"parts": [{"text": "respuesta Gemini"}]}}]}
        )

    with patch("qanda.services.agent_service.urlopen", fake_urlopen):
        result = GeminiStrategy(api_key="clave-gemini").generate("prompt de prueba")

    assert result == "respuesta Gemini"
    assert captured["url"].startswith(
        "https://generativelanguage.googleapis.com/"
    )
    assert captured["headers"]["x-goog-api-key"] == "clave-gemini"


def test_local_model_strategy_usa_el_modelo_configurado(monkeypatch):
    monkeypatch.setenv("LOCAL_MODEL_URL", "http://localhost:11434/api/generate")
    monkeypatch.setenv("LOCAL_MODEL_NAME", "llama3")
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data)
        return FakeResponse({"response": "respuesta local"})

    with patch("qanda.services.agent_service.urlopen", fake_urlopen):
        result = LocalModelStrategy().generate("prompt de prueba")

    assert result == "respuesta local"
    assert captured["url"] == "http://localhost:11434/api/generate"
    assert captured["body"]["model"] == "llama3"
    assert captured["body"]["prompt"] == "prompt de prueba"


def test_local_model_strategy_mantiene_texto_sin_url(monkeypatch):
    monkeypatch.delenv("LOCAL_MODEL_URL", raising=False)

    with patch(
        "qanda.services.agent_service.urlopen",
        side_effect=AssertionError("no debe llamar a ningún servidor"),
    ):
        result = LocalModelStrategy().generate("prompt de prueba")

    assert result.startswith("Respuesta generada automáticamente")


def test_openai_sin_clave_devuelve_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIStrategy().generate("prompt de prueba")


@pytest.mark.parametrize(
    ("strategy", "expected"),
    [
        (OpenAIStrategy(api_key="clave-openai"), "OpenAI devolvió un error"),
        (GeminiStrategy(api_key="clave-gemini"), "Gemini devolvió un error"),
    ],
)
def test_error_del_proveedor_se_informa_sin_clave(strategy, expected):
    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)

    with (
        patch("qanda.services.agent_service.urlopen", fake_urlopen),
        pytest.raises(RuntimeError, match=expected) as error,
    ):
        strategy.generate("prompt de prueba")

    assert "clave-openai" not in str(error.value)
    assert "clave-gemini" not in str(error.value)
