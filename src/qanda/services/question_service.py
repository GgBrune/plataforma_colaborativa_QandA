import re
from collections.abc import Iterable
from dataclasses import dataclass

from qanda.extensions import db
from qanda.models import Category, Question, Tag


@dataclass
class QuestionValidationError(ValueError):
    """Errores de validación de una pregunta, por campo."""

    errors: dict[str, str]

    def __str__(self):
        return "La pregunta no es válida: " + "; ".join(self.errors.values())


def parse_tags(tags: str | Iterable[str] | None) -> list[str]:
    """Convierte las etiquetas recibidas en nombres limpios y sin repetir.

    Acepta una cadena separada por comas (o saltos de línea) y también una
    colección de cadenas. La comparación para detectar repetidos no distingue
    mayúsculas, de modo que "Python" y "python" son la misma etiqueta.
    """
    if tags is None:
        parts = []
    elif isinstance(tags, str):
        parts = re.split(r"[,\n]", tags)
    elif isinstance(tags, Iterable):
        parts = []
        for item in tags:
            parts.extend(re.split(r"[,\n]", item) if isinstance(item, str) else [])
    else:
        parts = []

    names: list[str] = []
    seen: set[str] = set()
    for part in parts:
        name = " ".join(part.split())
        key = name.casefold()
        if name and key not in seen:
            seen.add(key)
            names.append(name)
    return names


def validate_tags(
    tags: str | Iterable[str] | None,
) -> tuple[list[str], dict[str, str]]:
    """Normaliza las etiquetas y devuelve los errores de validación encontrados."""
    names = parse_tags(tags)
    errors: dict[str, str] = {}
    if any(len(name) > Tag.NAME_MAX_LENGTH for name in names):
        errors["tags"] = (
            f"Las etiquetas no pueden superar los {Tag.NAME_MAX_LENGTH} caracteres."
        )
    return names, errors


def _resolve_tags(names: Iterable[str]) -> list[Tag]:
    """Reutiliza las etiquetas existentes y crea solo las que faltan."""
    resolved: list[Tag] = []
    by_key: dict[str, Tag] = {}
    for name in names:
        key = name.casefold()
        tag = by_key.get(key)
        if tag is None:
            tag = db.session.scalar(
                db.select(Tag).where(db.func.lower(Tag.name) == key)
            )
            if tag is None:
                tag = Tag(name=name)
                db.session.add(tag)
                db.session.flush()
            by_key[key] = tag
        resolved.append(tag)
    return resolved


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
    title: str,
    description: str,
    category: str,
    author,
    tags: str | Iterable[str] | None = "",
) -> Question:
    """Valida y persiste una pregunta, asignando automáticamente su fecha de publicación."""
    cleaned, errors = validate_question(title, description, category)
    tag_names, tag_errors = validate_tags(tags)
    errors.update(tag_errors)
    if errors:
        raise QuestionValidationError(errors)

    question = Question(
        title=cleaned["title"],
        description=cleaned["description"],
        category=cleaned["category"],
        author=author,
        tags=_resolve_tags(tag_names),
    )
    db.session.add(question)
    db.session.commit()
    return question


def update_question(
    question: Question,
    title: str,
    description: str,
    category: str,
    tags: str | Iterable[str] | None = "",
) -> Question:
    """Actualiza una pregunta existente, reemplazando sus etiquetas."""
    cleaned, errors = validate_question(title, description, category)
    tag_names, tag_errors = validate_tags(tags)
    errors.update(tag_errors)
    if errors:
        raise QuestionValidationError(errors)

    question.title = cleaned["title"]
    question.description = cleaned["description"]
    question.category = cleaned["category"]
    question.tags = _resolve_tags(tag_names)
    db.session.commit()
    return question
