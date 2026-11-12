from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from qanda.extensions import db
from qanda.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = db.session.scalar(db.select(User).where(User.email == email))

        if user is None or not user.check_password(password):
            flash("Email o contraseña incorrectos.", "error")
            return render_template("auth/login.html"), 401

        login_user(user)
        return redirect(url_for("health.health"))  # cambiar por la página principal

    return render_template("auth/login.html")


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))