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


# Proveedores disponibles. Las claves aceptan tanto el nombre del proveedor
# como el de la clase concreta para que el formulario del admin sea flexible.
STRATEGY_FACTORIES: dict[str, type[StrategyLLM]] = {
    "local": LocalModelStrategy,
    "localmodel": LocalModelStrategy,
    "localmodelstrategy": LocalModelStrategy,
    "openai": OpenAIStrategy,
    "openaistrategy": OpenAIStrategy,
    "gemini": GeminiStrategy,
    "geministrategy": GeminiStrategy,
}

# Opciones canónicas del selector de la interfaz de administración.
STRATEGY_CHOICES = (
    ("local", "Local"),
    ("openai", "OpenAI"),
    ("gemini", "Gemini"),
)

# None significa "todavía no la cambiaron": en ese caso se respeta la variable
# de entorno en cada lectura. Cuando el administrador elige una estrategia se
# guarda acá y pasa a usarse en todas las generaciones posteriores.
_current_strategy: StrategyLLM | None = None


def build_strategy(provider: str | StrategyLLM) -> StrategyLLM:
    """Crea la estrategia indicada por nombre o devuelve la instancia recibida."""
    if not isinstance(provider, str):
        if callable(getattr(provider, "generate", None)):
            return provider
        raise TypeError("La estrategia debe implementar generate(prompt).")

    key = provider.strip().casefold()
    strategy_class = STRATEGY_FACTORIES.get(key)
    if strategy_class is None:
        options = ", ".join(name for name, _ in STRATEGY_CHOICES)
        raise ValueError(f"Estrategia desconocida: {provider!r}. Opciones: {options}.")
    return strategy_class()


def get_strategy() -> StrategyLLM:
    """Devuelve la estrategia vigente del agente.

    Si el administrador no la cambió, se usa LLM_PROVIDER (local por defecto).
    """
    global _current_strategy
    if _current_strategy is None:
        _current_strategy = build_strategy(os.getenv("LLM_PROVIDER", "local"))
    return _current_strategy


def set_strategy(strategy: str | StrategyLLM) -> StrategyLLM:
    """Cambia la estrategia del agente sin necesidad de reiniciar la app."""
    global _current_strategy
    _current_strategy = build_strategy(strategy)
    return _current_strategy


setStrategy = set_strategy


def reset_strategy() -> None:
    """Vuelve a la estrategia configurada por entorno (útil en tests)."""
    global _current_strategy
    _current_strategy = None


def get_strategy_name() -> str:
    """Nombre de la estrategia vigente, para mostrarla en el formulario."""
    strategy = get_strategy()
    for name, strategy_class in STRATEGY_FACTORIES.items():
        if isinstance(strategy, strategy_class):
            return name
    return type(strategy).__name__


def _agent_get_strategy(self) -> StrategyLLM:
    return get_strategy()


def _agent_set_strategy(self, strategy: str | StrategyLLM) -> StrategyLLM:
    return set_strategy(strategy)


# models/user.py no se modifica: el contexto Strategy se completa desde acá,
# donde viven las estrategias concretas.
AutomaticAgent.strategy = property(_agent_get_strategy, _agent_set_strategy)
AutomaticAgent.setStrategy = _agent_set_strategy
AutomaticAgent.set_strategy = _agent_set_strategy


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
        tag.name.casefold().lstrip("#") == AGENT_TRIGGER_TAG for tag in question.tags
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
