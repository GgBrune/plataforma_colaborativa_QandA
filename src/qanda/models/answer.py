from datetime import datetime, timezone

from qanda.extensions import db


class Answer(db.Model):
    """Respuesta publicada por un usuario a una pregunta."""

    __tablename__ = "answers"

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    published_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    question_id = db.Column(
        db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    question = db.relationship("Question", back_populates="answers")
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = db.relationship("User", back_populates="answers")

    @property
    def is_automatic(self):
        return self.author.is_agent

    def __repr__(self):
        return f"<Answer {self.id} to question {self.question_id}>"
