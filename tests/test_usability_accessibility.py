"""Pruebas del issue #17: interfaz adaptable y errores comprensibles."""

import re
from pathlib import Path

from qanda.services.question_service import publish_question

BASE_URL = "https://localhost"


def _html(response):
    return response.get_data(as_text=True)


def _field_ids(html):
    """Ids de controles de formulario presentes en una página."""
    return set(re.findall(r'<(?:input|select|textarea)\b[^>]*\bid="([^"]+)"', html))


def test_root_entry_point_leads_to_the_question_list(client):
    response = client.get("/", base_url=BASE_URL)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/preguntas/")


def test_error_pages_explain_what_happened(client):
    response = client.get("/pagina-que-no-existe", base_url=BASE_URL)
    html = _html(response)

    assert response.status_code == 404
    assert "No encontramos esa página" in html
    assert 'role="alert"' in html
    assert "Volver al listado de preguntas" in html


def test_layout_is_adaptable_and_keyboard_accessible(client):
    html = _html(client.get("/preguntas/", base_url=BASE_URL))

    assert '<html lang="es">' in html
    assert 'name="viewport" content="width=device-width, initial-scale=1"' in html
    assert "css/styles.css" in html
    assert 'class="skip-link" href="#contenido"' in html
    assert '<main id="contenido" class="page" tabindex="-1">' in html
    assert 'aria-label="Navegación principal"' in html


def test_stylesheet_defines_tablet_and_mobile_breakpoints(app):
    css = (Path(app.root_path) / "static" / "css" / "styles.css").read_text(
        encoding="utf-8"
    )

    assert "@media (max-width: 900px)" in css
    assert "@media (max-width: 600px)" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in css
    assert "grid-template-columns: 1fr" in css
    assert "overflow-x: auto" in css
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css


def test_question_validation_errors_are_announced_and_linked(logged_in_client):
    response = logged_in_client.post(
        "/preguntas/nueva",
        base_url=BASE_URL,
        data={"title": "", "description": "", "category": "Python"},
    )
    html = _html(response)

    assert response.status_code == 400
    assert "El título es obligatorio." in html
    assert "La descripción es obligatoria." in html
    assert 'class="error-summary" role="alert"' in html
    assert 'href="#title"' in html
    assert 'href="#description"' in html
    assert 'id="title-error"' in html
    assert 'aria-invalid="true"' in html
    assert 'aria-describedby="title-hint title-error"' in html
    assert 'class="field-error" id="title-error"' in html


def test_answer_validation_error_is_announced_and_linked(logged_in_client, author):
    question = publish_question(
        "¿Cómo respondo?", "Detalle de la pregunta.", "Python", author
    )

    response = logged_in_client.post(
        f"/preguntas/{question.id}/respuestas",
        base_url=BASE_URL,
        data={"body": ""},
    )
    html = _html(response)

    assert response.status_code == 400
    assert "El cuerpo de la respuesta es obligatorio." in html
    assert 'id="body-error"' in html
    assert 'aria-describedby="body-hint body-error"' in html
    assert 'href="#body"' in html


def test_flash_messages_have_an_accessible_role(client, admin_client, author):
    failed = client.post(
        "/login",
        base_url=BASE_URL,
        data={"email": author.email, "password": "incorrecta"},
    )
    failed_html = _html(failed)
    assert failed.status_code == 401
    assert 'class="flash error" role="alert"' in failed_html
    assert 'aria-live="polite"' in failed_html

    changed = admin_client.post(
        f"/admin/usuarios/{author.id}/rol",
        base_url=BASE_URL,
        data={"role": "administrator"},
        follow_redirects=True,
    )
    html = _html(changed)
    assert changed.status_code == 200
    assert 'class="flash success" role="status"' in html


def test_every_form_control_has_a_label(client, logged_in_client, author, app):
    question = publish_question(
        "¿Puedo navegar con teclado?", "Quiero usar la plataforma sin mouse.",
        "Python", author,
    )
    pages = (
        client.get("/login", base_url=BASE_URL),
        logged_in_client.get("/preguntas/nueva", base_url=BASE_URL),
        logged_in_client.get(f"/preguntas/{question.id}", base_url=BASE_URL),
    )

    for page in pages:
        html = _html(page)
        for field_id in _field_ids(html):
            assert f'for="{field_id}"' in html, f"Falta etiqueta para {field_id}"


def test_admin_strategy_error_points_to_the_field(admin_client):
    response = admin_client.post(
        "/admin/estrategia", base_url=BASE_URL, data={"strategy": "desconocida"}
    )
    html = _html(response)

    assert response.status_code == 400
    assert 'class="field field--invalid"' in html
    assert 'aria-invalid="true"' in html
    assert 'aria-describedby="strategy-hint strategy-error"' in html
    assert 'id="strategy-error" role="alert"' in html


def test_user_table_is_labelled_on_small_screens(admin_client, author):
    html = _html(admin_client.get("/admin/usuarios", base_url=BASE_URL))

    assert 'role="region" aria-label="Listado de usuarios"' in html
    assert 'scope="col"' in html
    assert 'data-label="Email"' in html
    assert f'for="role-{author.id}"' in html
