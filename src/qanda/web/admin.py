from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from qanda.extensions import db
from qanda.models import User
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
