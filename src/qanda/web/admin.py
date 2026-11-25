from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from qanda.services.agent_service import (
    STRATEGY_CHOICES,
    get_strategy_name,
    set_strategy,
)
from qanda.web.decorators import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/usuarios")
@admin_required
def listar_usuarios():
    return "Administration panel"


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
