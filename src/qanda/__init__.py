from flask import Flask

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

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(questions_bp)
    app.cli.add_command(create_admin)

    return app
