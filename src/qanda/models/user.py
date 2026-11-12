from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from qanda.extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False) # var del rol de usuario

    __mapper_args__ = {"polymorphic_on": role}

    @property
    def is_admin(self):
        return self.role == "administrator"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<{type(self).__name__} {self.email}>"

class Administrator(User):
    __mapper_args__ = {"polymorphic_identity": "administrator"}
class GeneralUser(User):
    __mapper_args__ = {"polymorphic_identity": "general_user"}