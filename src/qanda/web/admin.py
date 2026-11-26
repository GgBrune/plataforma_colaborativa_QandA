from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from qanda.extensions import db
from qanda.models import User
from qanda.services.agent_service import (
    STRATEGY_CHOICES,
    get_strategy_name,
    set_strategy,
)
from qanda.services.user_service import (
    ROLE_LABELS,
    UserValidationError,
    change_user_role,
    list_users,
)
from qanda.web.decorators import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/usuarios")
@admin_required
def listar_usuarios():
    return render_template(
        "admin/users.html", users=list_users(), role_labels=ROLE_LABELS
    )


@admin_bp.post("/usuarios/<int:user_id>/rol")
@admin_required
def cambiar_rol(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)

    try:
        updated = change_user_role(user, request.form.get("role", ""))
    except UserValidationError as exc:
        flash(exc.errors["role"], "error")
    else:
        flash(
            f"El rol de {updated.email} se actualizó a {ROLE_LABELS[updated.role]}.",
            "success",
        )

    return redirect(url_for("admin.listar_usuarios"))


@admin_bp.route("/estrategia", methods=["GET", "POST"])
@login_required
@admin_required
def configurar_estrategia():
    """Permite al administrador elegir la estrategia LLM del agente."""
    error = ""

    if request.method == "POST":
        provider = next(
            (
                request.form.get(field, "").strip()
                for field in (
                    "strategy",
                    "provider",
                    "strategy_name",
                    "llm_provider",
                    "estrategia",
                    "proveedor",
                )
                if request.form.get(field, "").strip()
            ),
            "",
        )
        try:
            set_strategy(provider)
        except (TypeError, ValueError) as exc:
            error = str(exc)
        else:
            flash(f"Estrategia LLM cambiada a {get_strategy_name()}.", "success")
            return redirect(url_for("admin.configurar_estrategia"))

    return render_template(
        "admin/strategy.html",
        strategies=STRATEGY_CHOICES,
        current_strategy=get_strategy_name(),
        error=error,
    ), (400 if error else 200)
