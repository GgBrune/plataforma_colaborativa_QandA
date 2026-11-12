from flask import Flask

from qanda.config import Config
from qanda.extensions import db, login_manager
from qanda.web.auth import auth_bp


def create_app(config_class=Config):
    app = Flask(__name__)

    app.config.from_object(config_class)

    db.init_app(app)

    from qanda.api.health import health_bp
    from qanda.web.users import users_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(users_bp)

    return app

login_manager.init_app(app)
login_manager.login_view = "auth.login"

from qanda.models import User

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

app.register_blueprint(auth_bp)
