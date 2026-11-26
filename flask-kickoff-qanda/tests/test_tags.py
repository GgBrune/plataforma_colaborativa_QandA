import pytest

from qanda import create_app
from qanda.config import Config
from qanda.extensions import db
from qanda.models import GeneralUser, Question, Tag, question_tags
from qanda.services.question_service import (
    parse_tags,
    publish_question,
    update_question,
)


@pytest.fixture
def app(tmp_path):
    class TestConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret"
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'test.db'}"

    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def author(app):
    user = GeneralUser(email="author@example.com")
    user.set_password("secret")
    db.session.add(user)
    db.session.commit()
    return user


def login(client, user):
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True


def count_rows(table):
    return db.session.execute(
        db.select(db.func.count()).select_from(table)
    ).scalar_one()


def test_parse_tags_normalizes_and_deduplicates():
    assert parse_tags(" Python,  flask ,,python\nDjango ") == [
        "Python",
        "flask",
        "Django",
    ]
    assert parse_tags(["python", "Python ", "", None]) == ["python"]
    assert parse_tags(None) == []


def test_question_can_have_no_tags(app, author):
    question = publish_question("Sin etiquetas", "Descripción", "Python", author)
    assert question.tags == []


def test_publish_deduplicates_tags(app, author):
    question = publish_question(
        "Con etiquetas",
        "Descripción",
        "Python",
        author,
        tags="python, Flask, python, flask, ",
    )

    assert {tag.name for tag in question.tags} == {"python", "Flask"}
    assert count_rows(Tag) == 2
    assert count_rows(question_tags) == 2


def test_tags_are_shared_between_questions(app, author):
    first = publish_question("Uno", "Descripción", "Python", author, tags="python")
    second = publish_question("Dos", "Descripción", "Flask", author, tags="Python")

    assert count_rows(Tag) == 1
    assert first.tags == second.tags


def test_update_adds_and_removes_tags(app, author):
    question = publish_question(
        "Título", "Descripción", "Python", author, tags="python, flask"
    )

    update_question(
        question, "Nuevo título", "Otra descripción", "Flask", tags="python, django"
    )

    assert {tag.name for tag in question.tags} == {"python", "django"}
    assert count_rows(question_tags) == 2


def test_new_question_form_has_tags_field(client, author):
    login(client, author)
    response = client.get("/preguntas/nueva")

    assert response.status_code == 200
    assert b'name="tags"' in response.data


def test_new_question_with_tags(client, author):
    login(client, author)
    response = client.post(
        "/preguntas/nueva",
        data={
            "title": "Pregunta con etiquetas",
            "description": "Descripción",
            "category": "Python",
            "tags": "python, flask, python",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    question = db.session.scalar(db.select(Question))
    assert question is not None
    assert {tag.name for tag in question.tags} == {"python", "flask"}


def test_new_question_accepts_repeated_tag_fields(client, author):
    login(client, author)
    client.post(
        "/preguntas/nueva",
        data={
            "title": "Pregunta con etiquetas",
            "description": "Descripción",
            "category": "Python",
            "tags": ["python", "flask", "python"],
        },
    )

    question = db.session.scalar(db.select(Question))
    assert {tag.name for tag in question.tags} == {"python", "flask"}


def test_detail_shows_tags_and_empty_state(client, author):
    with_tags = publish_question(
        "Con etiquetas", "Descripción", "Python", author, tags="python"
    )
    without_tags = publish_question("Sin etiquetas", "Descripción", "Flask", author)

    assert b"python" in client.get(f"/preguntas/{with_tags.id}").data
    assert b"Sin etiquetas" in client.get(f"/preguntas/{without_tags.id}").data


def test_edit_form_shows_current_tags(client, author):
    question = publish_question(
        "Título", "Descripción", "Python", author, tags="python, flask"
    )
    login(client, author)

    response = client.get(f"/preguntas/{question.id}/editar")

    assert response.status_code == 200
    assert b'name="tags"' in response.data
    assert b'value="flask, python"' in response.data


def test_edit_question_changes_tags(client, author):
    question = publish_question(
        "Título", "Descripción", "Python", author, tags="python, flask"
    )
    login(client, author)

    response = client.post(
        f"/preguntas/{question.id}/editar",
        data={
            "title": "Título",
            "description": "Descripción",
            "category": "Python",
            "tags": "python, django",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert {tag.name for tag in question.tags} == {"python", "django"}


def test_other_user_cannot_edit_question(client, app, author):
    question = publish_question(
        "Título", "Descripción", "Python", author, tags="python"
    )
    other = GeneralUser(email="other@example.com")
    other.set_password("secret")
    db.session.add(other)
    db.session.commit()
    login(client, other)

    assert client.get(f"/preguntas/{question.id}/editar").status_code == 403


def test_edit_requires_login(client, app, author):
    question = publish_question(
        "Título", "Descripción", "Python", author, tags="python"
    )

    response = client.get(f"/preguntas/{question.id}/editar")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
