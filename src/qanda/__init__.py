from urllib.parse import urlsplit, urlunsplit

from flask import Flask, redirect, request
from werkzeug.middleware.proxy_fix import ProxyFix

from qanda.commands import create_admin
from qanda.config import Config
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

    if app.config.get("TRUST_PROXY"):
        # Detrás de un proxy TLS, el esquema real llega en X-Forwarded-Proto.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    if app.config.get("FORCE_HTTPS"):

        @app.before_request
        def require_https():
            if request.is_secure:
                return None
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

    return app
