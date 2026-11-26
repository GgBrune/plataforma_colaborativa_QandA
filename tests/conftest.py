import pytest

from qanda import create_app
from qanda.config import Config
from qanda.extensions import db
from qanda.models import Administrator, GeneralUser


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-only-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture
def app():
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
    user = GeneralUser(email="autor@example.com")
    user.set_password("clave123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def logged_in_client(client, author):
    with client.session_transaction() as session:
        session["_user_id"] = str(author.id)
        session["_fresh"] = True
    return client


@pytest.fixture
def admin(app):
    user = Administrator(email="admin@example.com")
    user.set_password("clave123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def admin_client(client, admin):
    with client.session_transaction() as session:
        session["_user_id"] = str(admin.id)
        session["_fresh"] = True
    return client
