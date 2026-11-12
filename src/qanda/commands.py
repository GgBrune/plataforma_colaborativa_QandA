# creates an administrator user
import click

from qanda.extensions import db
from qanda.models import Administrator


@click.command("create-admin")
@click.argument("email")
@click.password_option()
def create_admin(email, password):
    """Crea un usuario administrador."""
    admin = Administrator(email=email)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(f"Administrador {email} creado.")