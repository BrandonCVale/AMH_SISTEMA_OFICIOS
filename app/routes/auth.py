from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from app.services.servicio_autenticacion import ServicioAutenticacion

# Creamos el Blueprint
bp_auth = Blueprint("auth", __name__, url_prefix="/auth")


@bp_auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        servicio = ServicioAutenticacion()
        usuario = servicio.intentar_login(email, password)

        if usuario:
            login_user(usuario)
            flash("Has iniciado sesión correctamente.", "success")
            return redirect(url_for("inicio"))  # Redirige al home
        else:
            flash("Correo o contraseña incorrectos.", "error")

    return render_template("auth/login.html")


@bp_auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
