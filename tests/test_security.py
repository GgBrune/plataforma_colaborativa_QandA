"""Pruebas del issue #14: protección de credenciales y transporte HTTPS."""

import logging

import pytest
from click.testing import CliRunner

from qanda import create_app
from qanda.commands import create_admin
from qanda.config import Config
from qanda.extensions import db
from qanda.models import GeneralUser, User
from qanda.security import MIN_PASSWORD_LENGTH, WeakPasswordError


@pytest.fixture
def app(tmp_path):
    class TestConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret"
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'test.db'}"
        FORCE_HTTPS = False
        SESSION_COOKIE_SECURE = False

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
def secure_app(tmp_path):
    class SecureConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret"
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'secure.db'}"
        FORCE_HTTPS = True
        SESSION_COOKIE_SECURE = True

    app = create_app(SecureConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _make_user(email, password):
    user = GeneralUser(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def test_password_is_stored_only_as_a_hash(app):
    password = "ContrasenaSegura123"
    user = _make_user("hash@example.com", password)

    assert user.password_hash != password
    assert password not in user.password_hash
    assert user.password_hash.startswith("scrypt:")
    assert user.check_password(password)
    assert not user.check_password("OtraContrasena123")

    stored = db.session.execute(
        db.text("SELECT password_hash FROM users WHERE email = :email"),
        {"email": "hash@example.com"},
    ).scalar_one()
    assert stored == user.password_hash
    assert password not in stored


def test_password_must_have_at_least_eight_characters(app):
    user = GeneralUser(email="corta@example.com")
    short_password = "corto12"

    with pytest.raises(WeakPasswordError) as exc_info:
        user.set_password(short_password)

    assert user.password_hash is None
    assert MIN_PASSWORD_LENGTH == 8
    assert short_password not in str(exc_info.value)
    assert "8 caracteres" in str(exc_info.value)

    # El límite es inclusivo: 8 caracteres sí se aceptan.
    user.set_password("ocho1234")
    assert user.password_hash.startswith("scrypt:")


def test_login_never_logs_the_password(client, app, caplog):
    password = "ClaveSegura123!"
    wrong_password = "Incorrecta123!"
    _make_user("login@example.com", password)

    with caplog.at_level(logging.DEBUG):
        failed = client.post(
            "/login", data={"email": "login@example.com", "password": wrong_password}
        )
        success = client.post(
            "/login", data={"email": "login@example.com", "password": password}
        )

    assert failed.status_code == 401
    assert success.status_code == 302
    assert wrong_password not in caplog.text
    assert password not in caplog.text
    assert password not in failed.get_data(as_text=True)


def test_create_admin_rejects_short_password_without_storing_it(app):
    runner = CliRunner()
    email = "admin-corto@example.com"

    with app.app_context():
        result = runner.invoke(
            create_admin, [email], input="corto12\ncorto12\n"
        )
        assert result.exit_code != 0
        assert "corto12" not in result.output
        assert db.session.scalar(db.select(User).where(User.email == email)) is None


def test_create_admin_stores_only_the_hash(app):
    runner = CliRunner()
    email = "admin-seguro@example.com"
    password = "AdminSegura123"

    with app.app_context():
        result = runner.invoke(
            create_admin, [email], input=f"{password}\n{password}\n"
        )
        assert result.exit_code == 0
        admin = db.session.scalar(db.select(User).where(User.email == email))
        assert admin is not None
        assert password not in result.output
        assert admin.password_hash != password
        assert password not in admin.password_hash


def test_http_requests_are_redirected_to_https(secure_app):
    client = secure_app.test_client()

    response = client.get("/login", base_url="http://localhost")

    assert response.status_code == 308
    assert response.headers["Location"].startswith("https://localhost/login")


def test_https_requests_enable_hsts_and_secure_cookies(secure_app):
    client = secure_app.test_client()
    password = "HttpsSegura123"
    _make_user("https@example.com", password)

    page = client.get("/login", base_url="https://localhost")
    assert page.status_code == 200
    assert page.headers["Strict-Transport-Security"].startswith("max-age=")

    response = client.post(
        "/login",
        base_url="https://localhost",
        data={"email": "https@example.com", "password": password},
    )
    assert response.status_code == 302
    assert response.headers["Set-Cookie"]
    assert "Secure" in response.headers["Set-Cookie"]
