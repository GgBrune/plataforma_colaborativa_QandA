import pytest

from qanda import create_app
from qanda.config import Config
from qanda.extensions import db
from qanda.models import Administrator, GeneralUser
from qanda.services.agent_service import (
    GeminiStrategy,
    LocalModelStrategy,
    OpenAIStrategy,
    StrategyLLM,
    generate_answer_for,
    get_agent_author,
    get_strategy,
    reset_strategy,
)
from qanda.services.question_service import publish_question


@pytest.fixture(autouse=True)
def restore_strategy():
    reset_strategy()
    yield
    reset_strategy()


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
def admin(app):
    user = Administrator(email="admin@example.com")
    user.set_password("secret")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def general_user(app):
    user = GeneralUser(email="user@example.com")
    user.set_password("secret")
    db.session.add(user)
    db.session.commit()
    return user


def login(client, email):
    response = client.post("/login", data={"email": email, "password": "secret"})
    assert response.status_code == 302


def test_agent_mantiene_estrategia_inicial(app):
    with app.app_context():
        agent = get_agent_author()

    assert isinstance(agent.strategy, StrategyLLM)
    assert isinstance(agent.strategy, LocalModelStrategy)


def test_agente_cambia_estrategia_con_set_strategy(app):
    with app.app_context():
        agent = get_agent_author()
        agent.setStrategy("openai")

        assert isinstance(agent.strategy, OpenAIStrategy)
        assert isinstance(get_strategy(), OpenAIStrategy)


def test_admin_puede_cambiar_estrategia(client, app, admin):
    login(client, admin.email)
    html = client.get("/admin/estrategia").get_data(as_text=True)
    assert 'name="strategy"' in html
    assert 'value="gemini"' in html

    response = client.post("/admin/estrategia", data={"strategy": "gemini"})
    assert response.status_code == 302

    with app.app_context():
        assert isinstance(get_strategy(), GeminiStrategy)
        assert isinstance(get_agent_author().strategy, GeminiStrategy)


def test_usuario_comun_no_puede_cambiar_estrategia(client, general_user):
    login(client, general_user.email)

    response = client.post("/admin/estrategia", data={"strategy": "gemini"})

    assert response.status_code == 403
    assert isinstance(get_strategy(), LocalModelStrategy)


def test_usuario_no_autenticado_es_redirigido_al_login(client):
    response = client.get("/admin/estrategia")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    response = client.post("/admin/estrategia", data={"strategy": "gemini"})
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert isinstance(get_strategy(), LocalModelStrategy)


def test_generacion_posterior_usa_la_nueva_estrategia(client, app, admin, monkeypatch):
    monkeypatch.setattr(
        GeminiStrategy, "generate", lambda self, prompt: "respuesta de Gemini"
    )
    login(client, admin.email)

    response = client.post("/admin/estrategia", data={"strategy": "gemini"})
    assert response.status_code == 302

    with app.app_context():
        author = db.session.get(Administrator, admin.id)
        question = publish_question(
            "¿Qué es Strategy?", "Necesito un ejemplo", "Python", author, tags="ia-help"
        )
        answer = generate_answer_for(question)

        assert answer.body == "respuesta de Gemini"
        assert answer.author.is_agent
