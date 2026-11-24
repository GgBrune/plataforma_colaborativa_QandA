from datetime import datetime, timezone

from qanda.extensions import db


class Question(db.Model):
    """Pregunta publicada por un usuario de la plataforma."""

    __tablename__ = "questions"

    TITLE_MAX_LENGTH = 150
    DESCRIPTION_MAX_LENGTH = 5000

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(TITLE_MAX_LENGTH), nullable=False)
    description = db.Column(db.Text, nullable=False)
    published_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = db.relationship("User", back_populates="questions")

    def __repr__(self):
        return f"<Question {self.title!r}>"
