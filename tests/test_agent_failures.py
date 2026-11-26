import logging

import pytest

from qanda.extensions import db
from qanda.models import Answer, Question
from qanda.services import agent_service
from qanda.services.agent_service import (
    AgentGenerationError,
    StrategyLLM,
    generate_answer_for,
    reset_strategy,
    set_strategy,
)
from qanda.services.question_service import publish_question


@pytest.fixture(autouse=True)
def restore_strategy():
    reset_strategy()
    yield
    reset_strategy()


class FailingStrategy(StrategyLLM):
    """Proveedor que siempre falla."""

    def __init__(self):
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        raise RuntimeError("El proveedor no respondió")


class FlakyStrategy(StrategyLLM):
    """Proveedor que falla los primeros intentos y luego responde."""

    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _question(app, author, tags="ia-help"):
    return publish_question(
        "¿Qué es la tolerancia a fallos?",
        "Quiero saber cómo se comporta el agente.",
        "Python",
        author,
        tags=tags,
    )


def test_reintenta_hasta_obtener_una_respuesta(app, author, monkeypatch):
    monkeypatch.setattr(agent_service, "AGENT_MAX_ATTEMPTS", 3)
    strategy = FlakyStrategy(
        [RuntimeError("timeout"), RuntimeError("503"), "respuesta final"]
    )
    set_strategy(strategy)
    question = _question(app, author)

    answer = generate_answer_for(question)

    assert strategy.calls == 3
    assert answer.body == "respuesta final"
    assert len(question.answers) == 1


def test_agota_los_intentos_no_publica_y_registra_el_error(
    app, author, monkeypatch, caplog
):
    monkeypatch.setattr(agent_service, "AGENT_MAX_ATTEMPTS", 2)
    strategy = FailingStrategy()
    set_strategy(strategy)
    question = _question(app, author)

    with (
        caplog.at_level(logging.WARNING, logger="qanda.services.agent_service"),
        pytest.raises(AgentGenerationError) as exc_info,
    ):
        generate_answer_for(question)

    assert strategy.calls == 2
    assert exc_info.value.attempts == 2
    assert "después de 2 intentos" in str(exc_info.value)
    assert "Fallo el intento 1/2" in caplog.text
    assert "Fallo el intento 2/2" in caplog.text
    assert db.session.scalar(db.select(db.func.count()).select_from(Answer)) == 0


def test_publicacion_de_pregunta_no_se_interrumpe_y_informa_el_fallo(
    logged_in_client, caplog
):
    strategy = FailingStrategy()
    set_strategy(strategy)

    with caplog.at_level(logging.ERROR):
        response = logged_in_client.post(
            "/preguntas/nueva",
            data={
                "title": "Pregunta con agente caído",
                "description": "El proveedor de IA no responde.",
                "category": "Python",
                "tags": "ia-help",
            },
        )

    assert response.status_code == 302
    assert strategy.calls == 3
    assert db.session.scalar(db.select(db.func.count()).select_from(Question)) == 1
    assert db.session.scalar(db.select(db.func.count()).select_from(Answer)) == 0

    listing = logged_in_client.get("/preguntas/")
    assert listing.status_code == 200
    assert b"No se pudo generar la respuesta autom" in listing.data
    assert "No se pudo generar la respuesta automática para la pregunta" in caplog.text


def test_detalle_de_la_pregunta_sigue_funcionando_si_falla_el_agente(
    app, author, client, caplog
):
    question = _question(app, author)
    strategy = FailingStrategy()
    set_strategy(strategy)

    with caplog.at_level(logging.ERROR):
        response = client.get(f"/preguntas/{question.id}")

    assert response.status_code == 200
    assert b"No se pudo generar la respuesta autom" in response.data
    assert b"tolerancia a fallos" in response.data
    assert "No se pudo generar la respuesta automática para la pregunta" in caplog.text
