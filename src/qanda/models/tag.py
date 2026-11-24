from qanda.extensions import db

question_tags = db.Table(
    "question_tags",
    db.Column(
        "question_id",
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "tag_id",
        db.Integer,
        db.ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Tag(db.Model):
    """Etiqueta temática que puede asociarse a varias preguntas."""

    __tablename__ = "tags"

    NAME_MAX_LENGTH = 50

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(NAME_MAX_LENGTH), nullable=False, unique=True)

    # "Python" y "python" son la misma etiqueta: la unicidad también se
    # garantiza sin distinguir mayúsculas, no solo en la normalización.
    __table_args__ = (db.Index("ix_tags_name_lower", db.func.lower(name), unique=True),)

    questions = db.relationship(
        "Question", secondary=question_tags, back_populates="tags"
    )

    def __repr__(self):
        return f"<Tag {self.name!r}>"
