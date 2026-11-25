from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from qanda.extensions import db
from qanda.models import Category, Question, Tag
from qanda.services.question_service import (
    QuestionValidationError,
    parse_tags,
    publish_question,
    update_question,
)

questions_bp = Blueprint("questions", __name__, url_prefix="/preguntas")


def _first_arg(*names):
    """Devuelve el primer valor no vacío entre varios parámetros de la URL."""
    for name in names:
        value = request.args.get(name, "").strip()
        if value:
            return value
    return ""


def _text_terms():
    """Recoge el texto a buscar en título y descripción."""
    terms = []
    for name in ("q", "search", "query", "text", "texto", "buscar"):
        value = _first_arg(name)
        if value:
            terms.append(value)
    return terms


def _submitted_filter_tags():
    """Admite etiquetas separadas por comas y parámetros repetidos."""
    values = []
    for name in ("tags", "tag", "etiquetas"):
        values.extend(request.args.getlist(name))
    return parse_tags(values)


def _contains(expression, term):
    return expression.contains(term.casefold(), autoescape=True)


@questions_bp.route("/")
def list_questions():
    category_value = _first_arg("category", "categoria")
    tag_names = _submitted_filter_tags()
    text_terms = _text_terms()
    title_term = _first_arg("title")
    description_term = _first_arg("description")
    order = "asc" if _first_arg("order", "sort").casefold() == "asc" else "desc"

    filters = {
        "category": category_value,
        "tags": ", ".join(tag_names),
        "q": text_terms[0] if text_terms else "",
        "title": title_term,
        "description": description_term,
        "order": order,
    }
    filters["active"] = any(
        (category_value, tag_names, text_terms, title_term, description_term)
    )

    stmt = db.select(Question).options(selectinload(Question.tags))

    if category_value:
        category = next(
            (
                member
                for member in Category
                if member.value.casefold() == category_value.casefold()
            ),
            None,
        )
        # Una categoría inexistente no debe mostrar todas las preguntas.
        stmt = stmt.where(
            Question.category == category if category else db.false()
        )

    if tag_names:
        lowered = [name.casefold() for name in tag_names]
        stmt = stmt.where(Question.tags.any(db.func.lower(Tag.name).in_(lowered)))

    for term in text_terms:
        stmt = stmt.where(
            db.or_(
                _contains(db.func.lower(Question.title), term),
                _contains(db.func.lower(Question.description), term),
            )
        )
    if title_term:
        stmt = stmt.where(_contains(db.func.lower(Question.title), title_term))
    if description_term:
        stmt = stmt.where(
            _contains(db.func.lower(Question.description), description_term)
        )

    published_at = (
        Question.published_at.asc()
        if order == "asc"
        else Question.published_at.desc()
    )
    questions = db.session.scalars(stmt.order_by(published_at)).all()
    return render_template(
        "questions/list.html",
        questions=questions,
        filters=filters,
        categories=Category.choices(),
    )


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
