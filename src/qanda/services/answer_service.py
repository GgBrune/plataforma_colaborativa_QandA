from dataclasses import dataclass

from qanda.extensions import db
from qanda.models import Answer


@dataclass
class AnswerValidationError(ValueError):
    """Errores de validación de una respuesta, por campo."""

    errors: dict[str, str]

    def __str__(self):
        return "La respuesta no es válida: " + "; ".join(self.errors.values())


def validate_answer(body: str) -> tuple[str, dict[str, str]]:
    """Normaliza el cuerpo y devuelve los errores de validación encontrados."""
    cleaned = body.strip() if isinstance(body, str) else ""
    errors: dict[str, str] = {}
    if not cleaned:
        errors["body"] = "El cuerpo de la respuesta es obligatorio."
    return cleaned, errors


def publish_answer(body: str, question, author) -> Answer:
    """Valida y persiste una respuesta, asignando automáticamente su fecha de publicación."""
    cleaned, errors = validate_answer(body)
    if errors:
        raise AnswerValidationError(errors)

    answer = Answer(body=cleaned, question=question, author=author)
    db.session.add(answer)
    db.session.commit()
    return answer
