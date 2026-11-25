"""Respuestas automáticas generadas por un agente con patrón Strategy."""

import os
import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from qanda.extensions import db
from qanda.models import Answer, AutomaticAgent, User
from qanda.services.answer_service import publish_answer

AGENT_EMAIL = "agente.automatico@qanda.local"
AGENT_TRIGGER_TAG = os.getenv("AGENT_TRIGGER_TAG", "ia-help").casefold().lstrip("#")
AGENT_DELAY_HOURS = float(os.getenv("AGENT_DELAY_HOURS", "24"))


class StrategyLLM(ABC):
    """Interfaz común para los proveedores de generación de texto."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Devuelve el texto generado a partir del prompt."""


class LocalModelStrategy(StrategyLLM):
    """Estrategia que responde con un texto predefinido."""

    def generate(self, prompt: str) -> str:
        return (
            "Respuesta generada automáticamente por el agente de la plataforma. "
            "Revisá la categoría y las etiquetas de la pregunta para obtener contexto."
        )


class OpenAIStrategy(StrategyLLM):
    def generate(self, prompt: str) -> str:
        raise RuntimeError("OpenAI no está configurado en este entorno.")


class GeminiStrategy(StrategyLLM):
    def generate(self, prompt: str) -> str:
        raise RuntimeError("Gemini no está configurado en este entorno.")


def get_strategy() -> StrategyLLM:
    """Devuelve la estrategia indicada por LLM_PROVIDER (local por defecto)."""
    provider = os.getenv("LLM_PROVIDER", "local").casefold()
    if provider == "openai":
        return OpenAIStrategy()
    if provider == "gemini":
        return GeminiStrategy()
    return LocalModelStrategy()


def build_prompt(question) -> str:
    """Compone el prompt con los cuatro datos de la pregunta."""
    tags = ", ".join(tag.name for tag in question.tags)
    return (
        f"Título: {question.title}\n"
        f"Descripción: {question.description}\n"
        f"Categoría: {question.category.value}\n"
        f"Etiquetas: {tags or 'Sin etiquetas'}\n"
    )


def get_agent_author() -> AutomaticAgent:
    """Obtiene (o crea) el usuario que representa al agente automático."""
    agent = db.session.scalar(db.select(User).where(User.email == AGENT_EMAIL))
    if agent is None:
        agent = AutomaticAgent(email=AGENT_EMAIL)
        agent.set_password(secrets.token_urlsafe(32))
        db.session.add(agent)
        db.session.commit()
    return agent


def generate_answer_for(question) -> Answer:
    """Genera una respuesta del agente para la pregunta."""
    author = get_agent_author()
    prompt = build_prompt(question)
    return publish_answer(author.generate(prompt), question, author)


def _has_trigger_tag(question) -> bool:
    return any(
        tag.name.casefold().lstrip("#") == AGENT_TRIGGER_TAG
        for tag in question.tags
    )


def _is_unanswered_for_long_enough(question) -> bool:
    elapsed = datetime.now(timezone.utc).replace(tzinfo=None) - question.published_at
    return elapsed >= timedelta(hours=AGENT_DELAY_HOURS)


def should_generate_answer(question) -> bool:
    """Responde si tiene la etiqueta disparadora o si pasó el tiempo sin respuesta."""
    if question.answers:
        return False
    return _has_trigger_tag(question) or _is_unanswered_for_long_enough(question)


def maybe_generate_answer(question) -> Answer | None:
    """Genera la respuesta automática solo cuando corresponde."""
    if not should_generate_answer(question):
        return None
    return generate_answer_for(question)
