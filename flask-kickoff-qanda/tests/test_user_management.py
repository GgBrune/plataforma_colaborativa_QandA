import pytest

from qanda.extensions import db
from qanda.models import Administrator, GeneralUser, User
from qanda.services.user_service import (
    ADMIN_ROLE,
    GENERAL_ROLE,
    UserValidationError,
    change_user_role,
    list_users,
)


def test_list_users_shows_email_and_role(app, admin, author):
    users = list_users()

    assert [(user.email, user.role) for user in users] == [
        ("admin@example.com", ADMIN_ROLE),
        ("autor@example.com", GENERAL_ROLE),
    ]


def test_promote_general_user_to_administrator(app, author):
    user_id = author.id
    updated = change_user_role(author, ADMIN_ROLE)

    assert updated.role == ADMIN_ROLE
    assert isinstance(updated, Administrator)
    assert db.session.get(User, user_id).role == ADMIN_ROLE
    assert updated.check_password("clave123")


def test_demote_administrator_to_general_user(app, admin):
    user_id = admin.id
    updated = change_user_role(admin, GENERAL_ROLE)

    assert updated.role == GENERAL_ROLE
    assert isinstance(updated, GeneralUser)
    assert db.session.get(User, user_id).role == GENERAL_ROLE


def test_invalid_role_is_rejected(app, author):
    with pytest.raises(UserValidationError) as exc_info:
        change_user_role(author, "superuser")

    assert "no es válido" in exc_info.value.errors["role"]
    assert db.session.get(User, author.id).role == GENERAL_ROLE


def test_admin_can_list_users(admin_client, admin, author):
    response = admin_client.get("/admin/usuarios")

    assert response.status_code == 200
    assert b"admin@example.com" in response.data
    assert b"autor@example.com" in response.data
    assert b"Administrador" in response.data
    assert b"Usuario general" in response.data


def test_admin_can_promote_user_through_the_form(admin_client, author):
    user_id = author.id
    response = admin_client.post(
        f"/admin/usuarios/{user_id}/rol", data={"role": ADMIN_ROLE}
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/usuarios")
    assert db.session.get(User, user_id).role == ADMIN_ROLE


def test_admin_can_demote_user_through_the_form(admin_client, author):
    user_id = author.id
    change_user_role(author, ADMIN_ROLE)

    response = admin_client.post(
        f"/admin/usuarios/{user_id}/rol", data={"role": GENERAL_ROLE}
    )

    assert response.status_code == 302
    assert db.session.get(User, user_id).role == GENERAL_ROLE


def test_invalid_role_reports_an_error(admin_client, author):
    response = admin_client.post(
        f"/admin/usuarios/{author.id}/rol",
        data={"role": "superuser"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"El rol seleccionado no es v\xc3\xa1lido." in response.data
    assert db.session.get(User, author.id).role == GENERAL_ROLE


def test_general_user_cannot_manage_users(logged_in_client):
    assert logged_in_client.get("/admin/usuarios").status_code == 403
    assert (
        logged_in_client.post(
            "/admin/usuarios/1/rol", data={"role": ADMIN_ROLE}
        ).status_code
        == 403
    )


def test_anonymous_user_is_redirected_to_login(client):
    response = client.get("/admin/usuarios")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_unknown_user_returns_404(admin_client):
    response = admin_client.post("/admin/usuarios/999/rol", data={"role": ADMIN_ROLE})

    assert response.status_code == 404
