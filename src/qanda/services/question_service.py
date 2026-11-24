from dataclasses import dataclass

from qanda.extensions import db
from qanda.models import Question


@dataclass
class QuestionValidationError(ValueError):
    """Errores de validación de una pregunta, por campo."""

    errors: dict[str, str]

    def __str__(self):
        return "La pregunta no es válida: " + "; ".join(self.errors.values())


def validate_question(
    title: str, description: str
) -> tuple[dict[str, str], dict[str, str]]:
    """Normaliza los datos y devuelve los errores de validación encontrados."""
    cleaned = {
        "title": title.strip() if isinstance(title, str) else "",
        "description": description.strip() if isinstance(description, str) else "",
    }

    errors: dict[str, str] = {}
    if not cleaned["title"]:
        errors["title"] = "El título es obligatorio."
    elif len(cleaned["title"]) > Question.TITLE_MAX_LENGTH:
        errors["title"] = (
            f"El título no puede superar los {Question.TITLE_MAX_LENGTH} caracteres."
        )

    if not cleaned["description"]:
        errors["description"] = "La descripción es obligatoria."
    elif len(cleaned["description"]) > Question.DESCRIPTION_MAX_LENGTH:
        errors["description"] = (
            "La descripción no puede superar los "
            f"{Question.DESCRIPTION_MAX_LENGTH} caracteres."
        )

    return cleaned, errors


def publish_question(title: str, description: str, author) -> Question:
    """Valida y persiste una pregunta, asignando automáticamente su fecha de publicación."""
    cleaned, errors = validate_question(title, description)
    if errors:
        raise QuestionValidationError(errors)

    question = Question(
        title=cleaned["title"], description=cleaned["description"], author=author
    )
    db.session.add(question)
    db.session.commit()
    return question
