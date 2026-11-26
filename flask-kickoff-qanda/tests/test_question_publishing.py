from datetime import datetime, timezone

import pytest

from qanda.extensions import db
from qanda.models import Question
from qanda.services.question_service import (
    QuestionValidationError,
    publish_question,
    validate_question,
)


def test_publish_question_assigns_publication_date_and_author(app, author):
    question = publish_question(
        "¿Cómo funciona el patrón Strategy?",
        "Quisiera entender cuándo conviene aplicarlo.",
        "Python",
        author,
    )

    assert question.id is not None
    assert question.published_at is not None
    assert question.published_at <= datetime.now(timezone.utc).replace(tzinfo=None)
    assert question.author == author
    assert db.session.get(Question, question.id) is not None


@pytest.mark.parametrize(
    "title, description, expected_field",
    [
        ("", "Una descripción válida", "title"),
        ("   ", "Una descripción válida", "title"),
        (None, "Una descripción válida", "title"),
        ("Un título válido", "", "description"),
        ("Un título válido", "   ", "description"),
        ("Un título válido", None, "description"),
    ],
)
def test_empty_fields_are_rejected(app, title, description, expected_field):
    with pytest.raises(QuestionValidationError) as exc_info:
        publish_question(title, description, "Python", author=None)

    assert expected_field in exc_info.value.errors
    assert "obligator" in exc_info.value.errors[expected_field]
    assert db.session.scalar(db.select(db.func.count()).select_from(Question)) == 0


@pytest.mark.parametrize(
    "title, description, expected_field",
    [
        ("a" * (Question.TITLE_MAX_LENGTH + 1), "Descripción válida", "title"),
        ("Título válido", "d" * (Question.DESCRIPTION_MAX_LENGTH + 1), "description"),
    ],
)
def test_max_length_is_enforced(app, title, description, expected_field):
    with pytest.raises(QuestionValidationError) as exc_info:
        publish_question(title, description, "Python", author=None)

    assert expected_field in exc_info.value.errors
    assert "no puede superar" in exc_info.value.errors[expected_field]


def test_validation_reports_all_invalid_fields_at_once(app):
    cleaned, errors = validate_question("", "", "Python")

    assert cleaned == {"title": "", "description": "", "category": "Python"}
    assert set(errors) == {"title", "description"}


def test_authenticated_user_can_publish_through_the_form(logged_in_client, author):
    response = logged_in_client.post(
        "/preguntas/nueva",
        data={
            "title": "  ¿Cómo publico una pregunta?  ",
            "description": "  Necesito ayuda con el formulario.  ",
            "category": "Python",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    question = db.session.scalar(db.select(Question))
    assert question.title == "¿Cómo publico una pregunta?"
    assert question.description == "Necesito ayuda con el formulario."
    assert question.author_id == author.id

    detail = logged_in_client.get(response.headers["Location"])
    assert detail.status_code == 200
    assert "¿Cómo publico una pregunta?".encode() in detail.data
    assert b"Necesito ayuda con el formulario." in detail.data


def test_form_reports_validation_errors(logged_in_client):
    response = logged_in_client.post(
        "/preguntas/nueva",
        data={"title": "", "description": "", "category": "Python"},
    )

    assert response.status_code == 400
    assert "El título es obligatorio.".encode() in response.data
    assert "La descripción es obligatoria.".encode() in response.data
    assert db.session.scalar(db.select(db.func.count()).select_from(Question)) == 0


def test_form_reports_max_length_errors(logged_in_client):
    response = logged_in_client.post(
        "/preguntas/nueva",
        data={
            "title": "a" * (Question.TITLE_MAX_LENGTH + 1),
            "description": "d" * (Question.DESCRIPTION_MAX_LENGTH + 1),
            "category": "Python",
        },
    )

    assert response.status_code == 400
    assert "El título no puede superar los 150 caracteres.".encode() in response.data
    assert (
        "La descripción no puede superar los 5000 caracteres.".encode() in response.data
    )


def test_user_can_log_in_and_then_publish(client, author):
    login = client.post("/login", data={"email": author.email, "password": "clave123"})

    assert login.status_code == 302
    assert login.headers["Location"].endswith("/preguntas/")

    publication = client.post(
        "/preguntas/nueva",
        data={
            "title": "Pregunta tras login",
            "description": "Descripción tras login.",
            "category": "Python",
        },
    )
    assert publication.status_code == 302
    assert db.session.scalar(db.select(db.func.count()).select_from(Question)) == 1


def test_anonymous_user_cannot_publish(client):
    response = client.post(
        "/preguntas/nueva",
        data={
            "title": "Título",
            "description": "Descripción",
            "category": "Python",
        },
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert db.session.scalar(db.select(db.func.count()).select_from(Question)) == 0
