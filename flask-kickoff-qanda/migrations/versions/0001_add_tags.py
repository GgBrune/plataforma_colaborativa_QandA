"""add tags and question_tags

Revision ID: 0001_add_tags
Revises:
Create Date: 2026-11-24

La migración comprueba qué tablas existen para funcionar tanto sobre una base
creada con db.create_all() como sobre una base vacía.
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_add_tags"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(length=254), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=30), nullable=False),
        )

    if "questions" not in existing:
        op.create_table(
            "questions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(length=150), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column(
                "category",
                sa.Enum(
                    "Python",
                    "Flask",
                    "Bases de Datos",
                    name="question_category",
                    create_constraint=True,
                ),
                nullable=False,
            ),
            sa.Column("published_at", sa.DateTime(), nullable=False),
            sa.Column(
                "author_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
        )

    if "tags" not in existing:
        op.create_table(
            "tags",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=50), nullable=False, unique=True),
        )
        op.create_index(
            "ix_tags_name_lower", "tags", [sa.text("lower(name)")], unique=True
        )

    if "question_tags" not in existing:
        op.create_table(
            "question_tags",
            sa.Column(
                "question_id",
                sa.Integer(),
                sa.ForeignKey("questions.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "tag_id",
                sa.Integer(),
                sa.ForeignKey("tags.id", ondelete="CASCADE"),
                primary_key=True,
            ),
        )


def downgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if "question_tags" in existing:
        op.drop_table("question_tags")
    if "tags" in existing:
        op.drop_index("ix_tags_name_lower", table_name="tags")
        op.drop_table("tags")
