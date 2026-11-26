"""Comandos de administración de la plataforma."""

import click

from qanda.extensions import db
from qanda.models import Administrator
from qanda.security import MIN_PASSWORD_LENGTH, WeakPasswordError


@click.command("create-admin")
@click.argument("email")
@click.password_option(
    hide_input=True,
    confirmation_prompt=True,
    help=f"Contraseña (mínimo {MIN_PASSWORD_LENGTH} caracteres).",
)
def create_admin(email, password):
    """Crea un usuario administrador."""
    admin = Administrator(email=email)
    try:
        admin.set_password(password)
    except WeakPasswordError as exc:
        raise click.UsageError(str(exc)) from exc

    db.session.add(admin)
    db.session.commit()
    # Nunca se muestra la contraseña, solo se guarda su hash.
    click.echo(f"Administrador {email} creado.")
