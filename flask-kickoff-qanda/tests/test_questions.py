from datetime import datetime

import pytest

from qanda import create_app
from qanda.config import Config
from qanda.extensions import db
from qanda.models import GeneralUser
from qanda.services.question_service import publish_question


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


@pytest.fixture
def questions(app, author):
    first = publish_question(
        "Cómo usar Flask",
        "Rutas con Flask en la app",
        "Flask",
        author,
        tags="python, flask",
    )
    second = publish_question(
        "Iterar en Python",
        "No entiendo los bucles",
        "Python",
        author,
        tags="python",
    )
    third = publish_question(
        "Consultar SQLite",
        "Necesito ORDER BY en bases de datos",
        "Bases de Datos",
        author,
        tags="sql",
    )
    first.published_at = datetime(2026, 1, 1, 10, 0)
    second.published_at = datetime(2026, 1, 3, 10, 0)
    third.published_at = datetime(2026, 1, 2, 10, 0)
    db.session.commit()
    return first, second, third


def test_list_shows_title_category_tags_and_date(client, questions):
    response = client.get("/preguntas/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Cómo usar Flask" in html
    assert "Flask" in html
    assert "python" in html and "flask" in html
    assert "03/01/2026 10:00" in html


def test_list_is_sorted_by_publication_date_descending(client, questions):
    html = client.get("/preguntas/").get_data(as_text=True)

    titles = ["Iterar en Python", "Consultar SQLite", "Cómo usar Flask"]
    positions = [html.index(title) for title in titles]
    assert positions == sorted(positions)


def test_list_can_be_sorted_ascending(client, questions):
    html = client.get("/preguntas/?order=asc").get_data(as_text=True)

    titles = ["Cómo usar Flask", "Consultar SQLite", "Iterar en Python"]
    positions = [html.index(title) for title in titles]
    assert positions == sorted(positions)


def test_filter_by_category(client, questions):
    html = client.get("/preguntas/?category=Python").get_data(as_text=True)

    assert "Iterar en Python" in html
    assert "Cómo usar Flask" not in html
    assert "Consultar SQLite" not in html


def test_filter_by_tags_comma_separated_and_case_insensitive(client, questions):
    html = client.get("/preguntas/?tags=SQL").get_data(as_text=True)

    assert "Consultar SQLite" in html
    assert "Iterar en Python" not in html

    html = client.get("/preguntas/?tags=python,flask").get_data(as_text=True)
    assert "Cómo usar Flask" in html
    assert "Iterar en Python" in html
    assert "Consultar SQLite" not in html


def test_filter_by_repeated_tag_parameters(client, questions):
    html = client.get("/preguntas/?tags=python&tags=sql").get_data(as_text=True)

    assert "Cómo usar Flask" in html
    assert "Iterar en Python" in html
    assert "Consultar SQLite" in html


def test_filter_by_text_in_title_and_description(client, questions):
    html = client.get("/preguntas/?q=flask").get_data(as_text=True)
    assert "Cómo usar Flask" in html
    assert "Iterar en Python" not in html

    html = client.get("/preguntas/?q=ORDER").get_data(as_text=True)
    assert "Consultar SQLite" in html
    assert "Cómo usar Flask" not in html


def test_filters_are_combined(client, questions):
    html = client.get(
        "/preguntas/?category=Python&tags=python&q=iterar"
    ).get_data(as_text=True)

    assert "Iterar en Python" in html
    assert "Cómo usar Flask" not in html
    assert "Consultar SQLite" not in html


def test_unknown_category_returns_no_results(client, questions):
    response = client.get("/preguntas/?category=NoExiste")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "No hay preguntas que coincidan" in html
    for title in ("Cómo usar Flask", "Iterar en Python", "Consultar SQLite"):
        assert title not in html


def test_filter_form_keeps_selected_values(client, questions):
    html = client.get("/preguntas/?category=Flask&tags=python&q=rutas").get_data(
        as_text=True
    )

    assert 'name="category"' in html
    assert 'name="tags"' in html
    assert 'name="q"' in html
    assert 'value="python"' in html
    assert 'value="rutas"' in html


def test_detail_shows_question(client, questions):
    question = questions[0]
    html = client.get(f"/preguntas/{question.id}").get_data(as_text=True)

    assert "Cómo usar Flask" in html
    assert "Rutas con Flask en la app" in html
    assert "Flask" in html
    assert "python" in html and "flask" in html


def test_detail_of_missing_question_returns_404(client, questions):
    assert client.get("/preguntas/999999").status_code == 404
