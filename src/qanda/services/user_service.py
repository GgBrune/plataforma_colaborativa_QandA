from dataclasses import dataclass

from qanda.extensions import db
from qanda.models import User

ADMIN_ROLE = "administrator"
GENERAL_ROLE = "general_user"
ROLE_LABELS = {ADMIN_ROLE: "Administrador", GENERAL_ROLE: "Usuario general"}


@dataclass
class UserValidationError(ValueError):
    """Errores de validación de un usuario, por campo."""

    errors: dict[str, str]

    def __str__(self):
        return "El usuario no es válido: " + "; ".join(self.errors.values())


def list_users() -> list[User]:
    """Devuelve todos los usuarios ordenados por email."""
    return db.session.scalars(db.select(User).order_by(User.email)).all()


def change_user_role(user: User, new_role: str) -> User:
    """Cambia el rol de un usuario y lo recarga con su nueva clase polimórfica."""
    if new_role not in ROLE_LABELS:
        raise UserValidationError({"role": "El rol seleccionado no es válido."})

    user_id = user.id
    # Se actualiza la columna discriminadora con un UPDATE para que SQLAlchemy
    # no intente hacer flush de una instancia con una clase polimórfica vieja.
    db.session.execute(
        db.update(User).where(User.id == user_id).values(role=new_role),
        execution_options={"synchronize_session": False},
    )
    db.session.commit()

    # Se descarta la instancia en caché y se recarga con la clase que corresponde
    # al nuevo rol (Administrator o GeneralUser).
    db.session.expunge(user)
    return db.session.get(User, user_id)
