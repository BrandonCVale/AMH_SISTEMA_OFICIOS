from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user
from app.models.usuario import (
    crear_nuevo_usuario,
    eliminar_usuario as eliminar_usuario_db,
    obtener_todos_los_usuarios,
    obtener_roles,
    obtener_areas,
)
from app.models.oficio import obtener_todos_los_oficios_admin
from app.services.oficio_service import ServicioOficio

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
    lista_oficios = obtener_todos_los_oficios_admin()

    # 3. Las enviamos al html
    return render_template(
        "admin/panel.html",
        usuarios=lista_usuarios,
        roles=lista_roles,
        areas=lista_areas,
        oficios=lista_oficios
    )


# Ruta para crear un nuevo usuario
@bp_admin.route("/crear_usuario", methods=["GET", "POST"])
@login_required
def crear_usuario():
    # 1. Verificar permisos
    if not current_user.es_administrador:
        flash("No tienes permisos para acceder a esta zona.", "error")
        return redirect(url_for("auth.login"))

    # Si es POST, procesamos el formulario
    if request.method == "POST":
        # A. Capturamos los valores (como texto)
        rol_seleccionado = request.form.get("id_rol")
        area_seleccionada = request.form.get("id_area")

        if not rol_seleccionado or not area_seleccionada:
            flash("Debes seleccionar un rol y un área válidos.", "error")
            return redirect(url_for("admin.panel_de_administrador"))

        try:
            datos = {
                "nombre_completo": request.form["nombre_completo"],
                "correo_electronico": request.form["correo_electronico"],
                "contrasena_hash": request.form["contrasena_hash"],
                "puesto": request.form["puesto"],
                "id_rol": int(rol_seleccionado),
                "id_area": int(area_seleccionada),
            }

            # D. Guardar
            if crear_nuevo_usuario(datos):
                flash("Usuario creado correctamente.", "success")
            else:
                flash("Error al crear el usuario (¿Correo duplicado?).", "error")

        except ValueError:
            flash("Error técnico: Los roles o áreas no son números.", "error")

    # Al final, siempre regresamos al panel principal
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


@bp_admin.route("/eliminar_oficio/<int:id_oficio>", methods=["POST"])
@login_required
def eliminar_oficio(id_oficio):
    if not current_user.es_administrador:
        return redirect(url_for("auth.login"))
    
    servicio = ServicioOficio()
    exito, mensaje = servicio.eliminar_oficio_total(id_oficio)
    
    if exito:
        flash(mensaje, "success")
    else:
        flash(mensaje, "error")
        
    return redirect(url_for("admin.panel_de_administrador"))
