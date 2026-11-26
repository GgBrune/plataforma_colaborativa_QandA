from urllib.parse import urlsplit, urlunsplit

from flask import Flask, redirect, render_template, request, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from qanda.commands import create_admin
from qanda.config import DEVELOPMENT_SECRET_KEY, Config
from qanda.extensions import db, login_manager
from qanda.models import User
from qanda.web.admin import admin_bp
from qanda.web.auth import auth_bp
from qanda.web.questions import questions_bp


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    secret_key = app.config.get("SECRET_KEY")
    if (
        not app.config.get("TESTING")
        and (not secret_key or secret_key == DEVELOPMENT_SECRET_KEY)
    ):
        raise RuntimeError(
            "SECRET_KEY no configurado: define una clave aleatoria en el entorno "
            "para proteger las sesiones de los usuarios."
        )

    if app.config.get("TRUST_PROXY"):
        # Detrás de un proxy TLS, el esquema real llega en X-Forwarded-Proto.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    if app.config.get("FORCE_HTTPS"):

        @app.before_request
        def require_https():
            if request.is_secure:
                return None
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                # Un 308 reenviaría el cuerpo (con la contraseña) que ya viajó
                # por HTTP; se rechaza la petición sin procesarla.
                return "Las peticiones con datos solo se aceptan por HTTPS.", 403
            _scheme, netloc, path, query, fragment = urlsplit(request.url)
            https_url = urlunsplit(("https", netloc, path, query, fragment))
            # 308 conserva el método y el cuerpo de los formularios POST.
            return redirect(https_url, code=308)

        @app.after_request
        def add_hsts(response):
            if request.is_secure:
                max_age = app.config.get("HSTS_MAX_AGE", 31536000)
                response.headers["Strict-Transport-Security"] = (
                    f"max-age={max_age}; includeSubDomains"
                )
            return response

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(questions_bp)
    app.cli.add_command(create_admin)

    @app.get("/")
    def index():
        """Punto de entrada único: lleva al listado de preguntas."""
        return redirect(url_for("questions.list_questions"))

    @app.errorhandler(403)
    def forbidden(error):
        return (
            render_template(
                "errors/error.html",
                code=403,
                title="Acceso no permitido",
                message=(
                    "No tenés permiso para ver esta página. "
                    "Si creés que se trata de un error, contactá al administrador."
                ),
            ),
            403,
        )

    @app.errorhandler(404)
    def not_found(error):
        return (
            render_template(
                "errors/error.html",
                code=404,
                title="No encontramos esa página",
                message=(
                    "Puede que el enlace esté desactualizado. "
                    "Probá de nuevo o volvé al listado de preguntas."
                ),
            ),
            404,
        )

    @app.errorhandler(500)
    def internal_error(error):
        return (
            render_template(
                "errors/error.html",
                code=500,
                title="Ocurrió un problema inesperado",
                message="Intentá de nuevo en unos minutos. Tu última acción no se completó.",
            ),
            500,
        )

    return app
