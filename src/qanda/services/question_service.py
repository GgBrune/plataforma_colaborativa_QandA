from dataclasses import dataclass

from qanda.extensions import db
from qanda.models import Category, Question


@dataclass
class QuestionValidationError(ValueError):
    """Errores de validación de una pregunta, por campo."""

    errors: dict[str, str]

    def __str__(self):
        return "La pregunta no es válida: " + "; ".join(self.errors.values())


def validate_question(
    title: str, description: str, category: str
) -> tuple[dict[str, str], dict[str, str]]:
    """Normaliza los datos y devuelve los errores de validación encontrados."""
    cleaned = {
        "title": title.strip() if isinstance(title, str) else "",
        "description": description.strip() if isinstance(description, str) else "",
        "category": category.strip() if isinstance(category, str) else "",
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

    try:
        cleaned["category"] = Category(cleaned["category"])
    except ValueError:
        options = ", ".join(member.value for member in Category)
        errors["category"] = (
            "La categoría es obligatoria."
            if not cleaned["category"]
            else f"Categoría no válida. Las opciones son: {options}."
        )

    return cleaned, errors


def publish_question(
    title: str, description: str, category: str, author
) -> Question:
    """Valida y persiste una pregunta, asignando automáticamente su fecha de publicación."""
    cleaned, errors = validate_question(title, description, category)
    if errors:
        raise QuestionValidationError(errors)

    question = Question(
        title=cleaned["title"],
        description=cleaned["description"],
        category=cleaned["category"],
        author=author,
    )
    db.session.add(question)
    db.session.commit()
    return question
