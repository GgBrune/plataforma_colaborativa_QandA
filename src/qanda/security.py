"""Política de contraseñas compartida por todos los puntos de entrada."""

MIN_PASSWORD_LENGTH = 8


class WeakPasswordError(ValueError):
    """La contraseña no cumple la política mínima de seguridad."""


def validate_password(password: str) -> None:
    """Valida la longitud mínima sin incluir la contraseña en el error."""
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
        )
