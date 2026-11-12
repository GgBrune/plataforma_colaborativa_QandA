from flask import Blueprint
from qanda.web.decorators import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/usuarios")
@admin_required
def listar_usuarios():
    return "Administration panel"