import os


def _env_flag(name: str, default: bool) -> bool:
    """Interpreta una variable de entorno booleana (1/true/yes/on)."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///app.db",
    )

    # La aplicación solo se sirve por HTTPS: redirecciona HTTP y endurece cookies.
    FORCE_HTTPS = _env_flag("FORCE_HTTPS", True)
    # Activar solo detrás de un proxy que termina TLS y envía X-Forwarded-Proto.
    TRUST_PROXY = _env_flag("TRUST_PROXY", False)
    HSTS_MAX_AGE = int(os.getenv("HSTS_MAX_AGE", "31536000"))
    PREFERRED_URL_SCHEME = "https" if FORCE_HTTPS else "http"
    SESSION_COOKIE_SECURE = FORCE_HTTPS
    REMEMBER_COOKIE_SECURE = FORCE_HTTPS
