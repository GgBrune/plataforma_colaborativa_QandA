from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from qanda.extensions import db
from qanda.models import Question
from qanda.services.answer_service import AnswerValidationError, publish_answer
from qanda.services.question_service import QuestionValidationError, publish_question

questions_bp = Blueprint("questions", __name__, url_prefix="/preguntas")


@questions_bp.route("/")
def list_questions():
    questions = db.session.scalars(
        db.select(Question).order_by(Question.published_at.desc())
    ).all()
    return render_template("questions/list.html", questions=questions)


def _render_form(title="", description="", errors=None):
    return render_template(
        "questions/new.html",
        title=title,
        description=description,
        errors=errors or {},
        question_title_max=Question.TITLE_MAX_LENGTH,
        question_description_max=Question.DESCRIPTION_MAX_LENGTH,
    )


@questions_bp.route("/nueva", methods=["GET", "POST"])
@login_required
def new_question():
    if request.method == "POST":
        title = request.form.get("title", "")
        description = request.form.get("description", "")
        try:
            question = publish_question(
                title, description, current_user._get_current_object()
            )
        except QuestionValidationError as exc:
            return _render_form(title, description, exc.errors), 400

        flash("Tu pregunta se publicó correctamente.", "success")
        return redirect(url_for("questions.question_detail", question_id=question.id))

    return _render_form()


def _render_detail(question, errors=None, body=""):
    return render_template(
        "questions/detail.html",
        question=question,
        errors=errors or {},
        body=body,
    )


@questions_bp.route("/<int:question_id>")
def question_detail(question_id):
    question = db.session.get(Question, question_id)
    if question is None:
        abort(404)
    return _render_detail(question)


@questions_bp.post("/<int:question_id>/respuestas")
@login_required
def new_answer(question_id):
    question = db.session.get(Question, question_id)
    if question is None:
        abort(404)

    body = request.form.get("body", "")
    try:
        publish_answer(body, question, current_user._get_current_object())
    except AnswerValidationError as exc:
        return _render_detail(question, exc.errors, body), 400

    flash("Tu respuesta se publicó correctamente.", "success")
    return redirect(url_for("questions.question_detail", question_id=question.id))
