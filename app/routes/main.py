from flask import Blueprint, redirect, url_for
from flask_login import current_user

bp_main = Blueprint("main", __name__)


@bp_main.route("/")
def inicio():
    """
    Punto de entrada raíz del sistema.
    Evalúa el estado de la sesión y dirige al usuario a su área correspondiente.
    """
    # Si el usuario YA entró, lo mandamos a su panel
    if current_user.is_authenticated:
        return redirect(url_for("oficios.panel_control"))
    # Si NO ha entrado, lo mandamos al login automáticamente
    else:
        return redirect(url_for("auth.login"))
