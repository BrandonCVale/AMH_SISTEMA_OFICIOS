from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user
from app.models.usuario import (
    crear_nuevo_usuario,
    eliminar_usuario as eliminar_usuario_db,
    obtener_todos_los_usuarios,
    obtener_roles,
    obtener_areas,
)

# Creamos el Blueprint
bp_admin = Blueprint("admin", __name__, url_prefix="/admin")


# Ruta del panel de administrador
@bp_admin.route("/panel_de_administrador")
@login_required
def panel_de_administrador():
    # 1. Verificar que el usuario tenga id_rol de administrador.
    if not current_user.es_administrador:
        flash("No tienes permisos para acceder a esta zona.", "error")
        return redirect(url_for("auth.login"))

    # 2. Si es administador, cargamos su interfaz y usamos los models
    lista_usuarios = obtener_todos_los_usuarios()
    lista_roles = obtener_roles()
    lista_areas = obtener_areas()

    # 3. Las enviamos al html
    return render_template(
        "admin/panel.html",
        usuarios=lista_usuarios,
        roles=lista_roles,
        areas=lista_areas,
    )


# Ruta para crear un nuevo usuario
@bp_admin.route("/crear_usuario", methods=["GET", "POST"])
@login_required
def crear_usuario():
    # 1. Verificar que el usuario tenga id_rol de administrador.
    if not current_user.es_administrador:
        flash("No tienes permisos para acceder a esta zona.", "error")
        return redirect(url_for("auth.login"))

    # Si es administrador, recibimos los datos del formulario
    if request.method == "POST":
        datos = {
            "nombre_completo": request.form["nombre_completo"],
            "correo_electronico": request.form["correo_electronico"],
            "contrasena_hash": request.form["contrasena_hash"],
            "puesto": request.form["puesto"],
            "id_rol": request.form["id_rol"],
            "id_area": request.form["id_area"],
        }
        # Pasarle los datos al model
        nuevo_usuario = crear_nuevo_usuario(datos)

        if nuevo_usuario:
            flash("Usuario creado correctamente.", "success")
            return redirect(url_for("admin.crear_usuario"))
        else:
            flash("Error al crear el usuario.", "error")
    return redirect(url_for("admin.panel_de_administrador"))


# Ruta para eliminar usuarios
@bp_admin.route("/eliminar_usuario/<int:id_usuario>", methods=["GET", "POST"])
@login_required
def eliminar_usuario(id_usuario):
    # 1. Verificar que el usuario que intenta eliminar a un usuario sea administrador
    if not current_user.es_administrador:
        flash("No tienes permisos para acceder a esta zona.", "error")
        return redirect(url_for("auth.login"))
    # 2. Si es administrador, entonces...
    if request.method == "POST":
        if eliminar_usuario_db(id_usuario):
            flash("Usuario eliminado correctamente.", "success")
            return redirect(url_for("admin.panel_de_administrador"))
        else:
            flash("Error al eliminar el usuario.", "error")
    return redirect(url_for("admin.panel_de_administrador"))
