from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from qanda.extensions import db
from qanda.models import Category, Question, Tag
from qanda.services.question_service import (
    QuestionValidationError,
    publish_question,
    update_question,
)

questions_bp = Blueprint("questions", __name__, url_prefix="/preguntas")


@questions_bp.route("/")
def list_questions():
    questions = db.session.scalars(
        db.select(Question).order_by(Question.published_at.desc())
    ).all()
    return render_template("questions/list.html", questions=questions)


def _render_form(
    template="questions/new.html",
    title="",
    description="",
    category="",
    tags="",
    errors=None,
    question=None,
):
    return render_template(
        template,
        title=title,
        description=description,
        category=category,
        tags=tags,
        categories=Category.choices(),
        errors=errors or {},
        question=question,
        question_title_max=Question.TITLE_MAX_LENGTH,
        question_description_max=Question.DESCRIPTION_MAX_LENGTH,
        tag_name_max=Tag.NAME_MAX_LENGTH,
    )


def _tags_as_text(question):
    return ", ".join(tag.name for tag in question.tags)


def _submitted_tags():
    """Admite un campo con etiquetas separadas por comas o campos repetidos."""
    return ", ".join(value for value in request.form.getlist("tags") if value)


@questions_bp.route("/nueva", methods=["GET", "POST"])
@login_required
def new_question():
    if request.method == "POST":
        title = request.form.get("title", "")
        description = request.form.get("description", "")
        category = request.form.get("category", "")
        tags = _submitted_tags()
        try:
            question = publish_question(
                title,
                description,
                category,
                current_user._get_current_object(),
                tags=tags,
            )
        except QuestionValidationError as exc:
            return _render_form(
                title=title,
                description=description,
                category=category,
                tags=tags,
                errors=exc.errors,
            ), 400

        flash("Tu pregunta se publicó correctamente.", "success")
        return redirect(url_for("questions.question_detail", question_id=question.id))

    return _render_form()


@questions_bp.route("/<int:question_id>/editar", methods=["GET", "POST"])
@login_required
def edit_question(question_id):
    question = db.session.get(Question, question_id)
    if question is None:
        abort(404)
    if question.author_id != current_user.id:
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "")
        description = request.form.get("description", "")
        category = request.form.get("category", "")
        tags = _submitted_tags()
        try:
            update_question(question, title, description, category, tags=tags)
        except QuestionValidationError as exc:
            return _render_form(
                template="questions/edit.html",
                title=title,
                description=description,
                category=category,
                tags=tags,
                errors=exc.errors,
                question=question,
            ), 400

        flash("La pregunta se actualizó correctamente.", "success")
        return redirect(url_for("questions.question_detail", question_id=question.id))

    return _render_form(
        template="questions/edit.html",
        title=question.title,
        description=question.description,
        category=question.category.value,
        tags=_tags_as_text(question),
        question=question,
    )


@questions_bp.route("/<int:question_id>")
def question_detail(question_id):
    question = db.session.get(Question, question_id)
    if question is None:
        abort(404)
    return render_template("questions/detail.html", question=question)
