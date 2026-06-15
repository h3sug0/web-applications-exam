from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from app.models import User


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_value = request.form.get("login", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(login=login_value).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Невозможно аутентифицироваться с указанными логином и паролем", "danger")
            return render_template("login.html", login_value=login_value)

        session.clear()
        session.permanent = bool(request.form.get("remember"))
        session["user_id"] = user.id
        flash("Вы успешно вошли в систему", "success")
        return redirect(request.args.get("next") or url_for("books.index"))

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Вы вышли из системы", "success")
    return redirect(request.referrer or url_for("books.index"))
