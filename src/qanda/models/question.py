from datetime import datetime, timezone
from enum import Enum

from qanda.extensions import db


class Category(str, Enum):
    """Categorías permitidas para clasificar una pregunta."""

    PYTHON = "Python"
    FLASK = "Flask"
    BASES_DE_DATOS = "Bases de Datos"

    @classmethod
    def choices(cls):
        """Devuelve pares (valor, etiqueta) para poblar un selector."""
        return [(member.value, member.value) for member in cls]


class Question(db.Model):
    """Pregunta publicada por un usuario de la plataforma."""

    __tablename__ = "questions"

    TITLE_MAX_LENGTH = 150
    DESCRIPTION_MAX_LENGTH = 5000

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(TITLE_MAX_LENGTH), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(
        db.Enum(
            Category,
            name="question_category",
            values_callable=lambda enum: [member.value for member in enum],
            create_constraint=True,
        ),
        nullable=False,
    )
    published_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = db.relationship("User", back_populates="questions")

    def __repr__(self):
        return f"<Question {self.title!r}>"
