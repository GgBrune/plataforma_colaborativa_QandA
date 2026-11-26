import pytest

from qanda.extensions import db
from qanda.models import Answer, GeneralUser
from qanda.services.answer_service import (
    AnswerValidationError,
    publish_answer,
    validate_answer,
)
from qanda.services.question_service import publish_question


@pytest.fixture
def question(app, author):
    return publish_question(
        "¿Cómo colaboro en la comunidad?", "Detalle de la pregunta.", "Python", author
    )


@pytest.fixture
def other_user(app):
    user = GeneralUser(email="otro@example.com")
    user.set_password("clave456")
    db.session.add(user)
    db.session.commit()
    return user


def test_a_question_can_receive_multiple_answers(app, question, author, other_user):
    first = publish_answer("Primera respuesta", question, author)
    second = publish_answer("Segunda respuesta", question, other_user)

    assert len(question.answers) == 2
    assert {answer.body for answer in question.answers} == {
        "Primera respuesta",
        "Segunda respuesta",
    }
    assert first.author_id == author.id
    assert second.author_id == other_user.id
    assert all(answer.question_id == question.id for answer in question.answers)
    assert all(answer.published_at is not None for answer in question.answers)


@pytest.mark.parametrize("body", ["", "   ", None])
def test_empty_body_is_rejected(app, question, author, body):
    with pytest.raises(AnswerValidationError) as exc_info:
        publish_answer(body, question, author)

    assert "body" in exc_info.value.errors
    assert "obligatorio" in exc_info.value.errors["body"]
    assert db.session.scalar(db.select(db.func.count()).select_from(Answer)) == 0


def test_validate_answer_strips_the_body(app):
    cleaned, errors = validate_answer("  Respuesta con espacios  ")

    assert cleaned == "Respuesta con espacios"
    assert errors == {}


def test_authenticated_user_can_answer_through_the_form(
    logged_in_client, question, author
):
    response = logged_in_client.post(
        f"/preguntas/{question.id}/respuestas",
        data={"body": "  Esta es mi respuesta.  "},
    )

    assert response.status_code == 302
    answer = db.session.scalar(db.select(Answer))
    assert answer.body == "Esta es mi respuesta."
    assert answer.author_id == author.id
    assert answer.question_id == question.id

    detail = logged_in_client.get(response.headers["Location"])
    assert detail.status_code == 200
    assert b"Esta es mi respuesta." in detail.data
    assert b"Respuestas (1)" in detail.data


def test_user_can_answer_another_users_question(client, question, other_user):
    with client.session_transaction() as session:
        session["_user_id"] = str(other_user.id)
        session["_fresh"] = True

    response = client.post(
        f"/preguntas/{question.id}/respuestas",
        data={"body": "Respuesta de otro usuario."},
    )

    assert response.status_code == 302
    answer = db.session.scalar(db.select(Answer))
    assert answer.author_id == other_user.id
    assert answer.question_id == question.id
    assert answer.author_id != question.author_id


def test_form_reports_empty_body_error(logged_in_client, question):
    response = logged_in_client.post(
        f"/preguntas/{question.id}/respuestas", data={"body": ""}
    )

    assert response.status_code == 400
    assert b"El cuerpo de la respuesta es obligatorio." in response.data
    assert db.session.scalar(db.select(db.func.count()).select_from(Answer)) == 0


def test_anonymous_user_cannot_answer(client, question):
    response = client.post(
        f"/preguntas/{question.id}/respuestas", data={"body": "Intento anónimo"}
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert db.session.scalar(db.select(db.func.count()).select_from(Answer)) == 0


def test_answer_to_unknown_question_returns_404(logged_in_client):
    response = logged_in_client.post("/preguntas/999/respuestas", data={"body": "Hola"})

    assert response.status_code == 404
