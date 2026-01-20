from flask import Blueprint, jsonify, redirect, render_template, request, url_for, flash
from flask_login import login_required, current_user
from app.models.catalogo import obtener_areas_activas
from app.services.oficio_service import ServicioOficio
from app.models.oficio import (
    obtener_oficios_del_gestor,
    obtener_bandeja_entrada_subdirector,
    obtener_documentos_de_un_oficio,
    obtener_kpis_gestor,
    obtener_kpis_subdirector,
    obtenter_los_detalles_de_un_oficio,
)
from app.models.usuario import obtener_juds_por_area

# Creamos el Blueprint
bp_oficios = Blueprint("oficios", __name__, url_prefix="/oficios")


# Ruta para el Panel de Control (Dashboard)
@bp_oficios.route("/panel_de_control")
@login_required
def panel_control():
    """
    Renderiza la pantalla principal según el rol del usuario.
    """
    # 1. Verificación para GESTOR
    if current_user.es_gestor:
        # Obtenemos los oficios del gestor para pasarselos a la tabla en su html
        mis_oficios = obtener_oficios_del_gestor(current_user.id)
        mis_kpis = obtener_kpis_gestor(current_user.id)

        return render_template(
            "oficios/dashboard_gestor.html",
            usuario=current_user,
            oficios=mis_oficios,
            kpis=mis_kpis,
        )

    # 2. Verificación para SUBDIRECTOR
    elif current_user.es_subdirector:
        # BUSCAR LOS OFICIOS DE SU AREA
        mis_oficios = obtener_bandeja_entrada_subdirector(current_user.id_area)
        mis_kpis = obtener_kpis_subdirector(current_user.id_area)

        return render_template(
            "oficios/dashboard_subdirector.html",
            usuario=current_user,
            oficios=mis_oficios,
            kpis=mis_kpis,
        )

    # 3. Verificación para JUD
    elif current_user.es_jud:
        return render_template("oficios/dashboard_jud.html", usuario=current_user)

    # 4. Fallback (Por si alguien no tiene rol)
    else:
        return "Acceso no identificado", 403


@bp_oficios.route("/crear_oficio", methods=["GET", "POST"])
@login_required
def crear_oficio():
    # 1. Seguridad: Solo gestores
    if not current_user.es_gestor:
        return redirect(url_for("oficios.panel_control"))

    # 2. Si el usuario envía el formulario (POST)
    if request.method == "POST":
        # Recolectamos los datos del formulario
        formulario = {
            "folio": request.form["folio"],
            "id_area": request.form["id_area"],
            "asunto": request.form["asunto"],
            "descripcion_solicitud": request.form["descripcion_solicitud"],
            "correo_adicional": request.form["correo_adicional"],
        }

        # Recolectamos los archivos
        archivo_principal = request.files.get("archivo")
        lista_anexos = request.files.getlist("anexos")  # Lista de múltiples archivos

        # Llamamos al servicio para que procese todo
        servicio = ServicioOficio()
        exito, mensaje = servicio.procesar_nuevo_oficio(
            formulario, archivo_principal, lista_anexos, current_user
        )

        # 3. Respuesta al usuario
        if exito:
            # Si todo salió bien, mensaje verde y al panel
            flash(mensaje, "success")
            return redirect(url_for("oficios.panel_control"))
        else:
            # Si falló (ej: Folio duplicado), mensaje rojo y se queda en el formulario
            flash(mensaje, "error")

    # 4. Si el usuario solo quiere VER el formulario (GET) o si falló el POST
    lista_areas = obtener_areas_activas()

    return render_template(
        "oficios/crear_formulario.html", usuario=current_user, areas=lista_areas
    )


@bp_oficios.route("/reasignar_oficio/<int:id_oficio>", methods=["GET", "POST"])
@login_required
def reasignar_oficio(id_oficio):

    # Solo los subdirectores pueden entrar
    if not current_user.es_subdirector:
        flash("No tienes permisos para acceder a esta zona.", "error")
        return redirect(url_for("oficios.panel_control"))

    # 1. Obtener los detalles y archivos de un oficio
    detalles_oficio = obtenter_los_detalles_de_un_oficio(id_oficio)
    archivos = obtener_documentos_de_un_oficio(id_oficio)

    if not detalles_oficio:
        flash("El oficio no existe o no se pudo cargar.", "error")
        return redirect(url_for("oficios.panel_control"))

    # 2. Obtener a los juds del area
    mis_juds = obtener_juds_por_area(current_user.id_area)

    if not mis_juds:
        flash("No hay JUDs registrados en tu área para asignar.", "warning")

    # 3. Renderizar la plantilla
    return render_template(
        "oficios/revisar_asignar.html",
        oficio=detalles_oficio,
        juds=mis_juds,
        archivos_del_oficio=archivos,
    )


@bp_oficios.route("/api/subdirector/<int:id_area>")
@login_required
def api_obtener_subdirector(id_area):
    """
    Ruta interna para AJAX. Retorna JSON con datos del subdirector.
    """
    from app.models.usuario import obtener_subdirector_por_area

    subdirector = obtener_subdirector_por_area(id_area)

    if subdirector:
        return jsonify(
            {
                "encontrado": True,
                "nombre": subdirector["nombre_completo"],
                "puesto": subdirector["puesto"],
                "correo": subdirector["correo_electronico"],
            }
        )
    else:
        return jsonify({"encontrado": False})
