import os
from flask import current_app
from flask import Blueprint, jsonify, redirect, render_template, request, url_for, flash
from flask_login import login_required, current_user
from app.models.catalogo import obtener_areas_activas
from app.services.oficio_service import ServicioOficio
from app.services.email_service import enviar_notificacion_oficio_turnado
from app.models.oficio import (
    obtener_oficios_del_gestor,
    obtener_bandeja_entrada_subdirector,
    obtener_documentos_de_un_oficio,
    obtener_kpis_gestor,
    obtener_kpis_subdirector,
    obtenter_los_detalles_de_un_oficio,
    marcar_oficio_como_visto,
    asignar_oficio_a_jud_db,
    obtener_historial_de_un_oficio,
    obtener_oficios_asignados_a_un_jud,
    oficios_atendidos_por_un_jud,
    obtener_peticiones_del_jud,
    obtener_solicitudes_de_mis_juds,
    obtener_detalles_peticion,
    obtener_archivos_peticion,
    registrar_respuesta_peticion_db,
    obtener_kpis_jud,
    obtener_oficios_atendidos_del_subdirector,
    obtener_a_todos_los_gestores,
)
from app.models.usuario import obtener_juds_por_area, buscar_usuario_por_id

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
        mis_oficios = obtener_bandeja_entrada_subdirector(current_user.id)
        mis_kpis = obtener_kpis_subdirector(current_user.id, current_user.id_area)
        # Obtener las peticiones de mis juds
        peticiones_de_mis_juds = obtener_solicitudes_de_mis_juds(current_user.id)
        # Obtener el historial de atendidos (Oficios que ya no están en estatus 1)
        mis_atendidos = obtener_oficios_atendidos_del_subdirector(current_user.id_area)

        print(mis_kpis)

        return render_template(
            "oficios/dashboard_subdirector.html",
            usuario=current_user,
            oficios=mis_oficios,
            kpis=mis_kpis,
            peticiones=peticiones_de_mis_juds,
            atendidos=mis_atendidos,
        )

    # 3. Verificación para JUD
    elif current_user.es_jud:
        # Obtener kpis
        mis_kpis = obtener_kpis_jud(current_user.id)
        # Traer los oficios PENDIENTES del jud
        mis_oficios = obtener_oficios_asignados_a_un_jud(current_user.id)
        # Traer los oficios ATENDIDOS del jud
        oficios_atendidos = oficios_atendidos_por_un_jud(current_user.id)
        # Traer las peticiones hechas por el jud
        mis_peticiones = obtener_peticiones_del_jud(current_user.id)

        return render_template(
            "oficios/dashboard_jud.html",
            usuario=current_user,
            oficios=mis_oficios,
            atendidos=oficios_atendidos,
            peticiones=mis_peticiones,
            kpis=mis_kpis,
        )

    # 4. Verificacion para administrador
    elif current_user.es_administrador:

        return redirect(url_for("admin.panel_de_administrador"))

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


@bp_oficios.route("/ver_detalles_oficio/<int:id_oficio>")
@login_required
def ver_detalles_oficio(id_oficio):
    # 1. Obtener los detalles y archivos de un oficio
    detalles = obtenter_los_detalles_de_un_oficio(id_oficio)
    archivos = obtener_documentos_de_un_oficio(id_oficio)
    historial = obtener_historial_de_un_oficio(id_oficio)

    # 2. Renderizar la plantilla
    return render_template(
        "oficios/ver_detalles.html",
        oficio=detalles,
        archivos_del_oficio=archivos,
        historial=historial,
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

    # Marcamos la hora de lectura (Solo si es la primera vez que lo abre)
    marcar_oficio_como_visto(id_oficio, current_user.id)

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


@bp_oficios.route("/turnar_oficio_a_jud/<int:id_oficio>", methods=["POST"])
@login_required
def turnar_oficio_a_jud(id_oficio):
    # Seguridad: Solo subdirectores
    if not current_user.es_subdirector:
        return redirect(url_for("oficios.panel_control"))

    # Obtenemos el ID del JUD desde el <select> del formulario
    id_jud_seleccionado = request.form.get("id_jud")
    instrucciones = request.form.get("instrucciones")

    if asignar_oficio_a_jud_db(
        id_oficio, id_jud_seleccionado, current_user.id, instrucciones
    ):
        # ENVIO DE CORREO AL JUD CON ARCHIVOS
        try:
            # Obtener los datos del jud (correo)
            jud = buscar_usuario_por_id(id_jud_seleccionado)
            # Obtener los detalles del oficio (asunto y folio)
            detalles_oficio = obtenter_los_detalles_de_un_oficio(id_oficio)
            # Obtener los archivos de este oficio (las rutas)
            archivos = obtener_documentos_de_un_oficio(id_oficio)

            # Crear la lista de rutas para los archivos
            rutas_para_correo = []
            if archivos:
                for archivo in archivos:
                    ruta_relativa = archivo["ruta_almacenamiento"]
                    ruta_absoluta = os.path.join(
                        current_app.root_path, "static", ruta_relativa
                    )
                    rutas_para_correo.append(ruta_absoluta)

            datos_email = {
                "folio_interno": detalles_oficio["folio_interno"],
                "asunto": detalles_oficio["asunto"],
                "descripcion": detalles_oficio["descripcion_solicitud"],
            }
            # Enviar correo
            enviar_notificacion_oficio_turnado(
                datos_email, jud.correo_electronico, rutas_para_correo
            )

            flash(
                "Oficio asignado al JUD y notificado por correo correctamente.",
                "success",
            )

        except Exception as e:
            flash(
                "Oficio asignado correctamente, pero hubo un error al notificar por correo al JUD.",
                "error",
            )
            print(f"Error al enviar correo al jud: {e}")
    else:
        flash("Ocurrió un error al intentar asignar el oficio.", "error")

    return redirect(url_for("oficios.panel_control"))


@bp_oficios.route("atender_oficio/<int:id_oficio>", methods=["GET", "POST"])
@login_required
def atender_oficio(id_oficio):
    # 1. Seguridad para que solo entren JUDs
    if not current_user.es_jud:
        return redirect(url_for("oficios.panel_control"))

    # 1.1 Obtener los detalles y archivo del oficio
    detalles = obtenter_los_detalles_de_un_oficio(id_oficio)
    archivos = obtener_documentos_de_un_oficio(id_oficio)

    # 2. LOGICA POST
    # 2.1 Obtener los datos del form
    if request.method == "POST":
        texto_respuesta = request.form.get("texto_respuesta")
        archivo = request.files.get("archivo")

        # 2.2 Procesar la respuesta del jud (texto y archivo)
        servicio = ServicioOficio()
        exito, mensaje = servicio.procesar_respuesta_jud(
            id_oficio, current_user.id, texto_respuesta, archivo
        )

        if exito:
            flash(mensaje, "success")
            return redirect(url_for("oficios.panel_control"))
        else:
            flash(mensaje, "error")

    return render_template(
        "oficios/atender.html",
        oficio=detalles,
        documentos=archivos,
    )


@bp_oficios.route("/nueva_peticion", methods=["GET", "POST"])
@login_required
def nueva_peticion():
    if request.method == "POST":
        # 1. Recolectar datos
        formulario = {
            "asunto": request.form["asunto"],
            "folio": request.form["folio"],
            "descripcion_solicitud": request.form["descripcion_solicitud"],
        }
        archivo = request.files.get("archivo")

        # 2. Llamar al servicio específico de peticiones
        servicio = ServicioOficio()
        exito, mensaje = servicio.procesar_peticion_jud(
            formulario, archivo, current_user
        )

        if exito:
            flash(mensaje, "success")
            return redirect(url_for("oficios.panel_control"))
        else:
            flash(mensaje, "error")

    return render_template("oficios/peticion_jud.html", usuario=current_user)


@bp_oficios.route("/nueva_peticion_subdirector", methods=["GET", "POST"])
@login_required
def nueva_peticion_subdirector():
    lista_gestores = obtener_a_todos_los_gestores()

    if request.method == "POST":
        formulario = {
            "asunto": request.form["asunto"],
            "folio": request.form["folio"],
            "descripcion_solicitud": request.form["descripcion_solicitud"],
        }
        archivo = request.files.get("archivo")

        servicio = ServicioOficio()
        exito, mensaje = servicio.procesar_peticion_subdirector(
            formulario, archivo, current_user
        )

        if exito:
            flash(mensaje, "success")
            return redirect(url_for("oficios.panel_control"))
        else:
            flash(mensaje, "error")

    return render_template(
        "oficios/peticion_subdirector.html",
        usuario=current_user,
        gestores=lista_gestores,
    )


@bp_oficios.route(
    "/responder_peticion_de_jud/<int:id_peticion>", methods=["GET", "POST"]
)
@login_required
def responder_peticion_de_jud(id_peticion):
    # Obtenemos la informacion de la peticion
    info_peticion = obtener_detalles_peticion(id_peticion)
    archivos_peticion = obtener_archivos_peticion(id_peticion)

    if request.method == "POST":
        # Recibir los datos del formualario (id_et)
        id_peticion = request.form.get("id_peticion")
        texto_respuesta = request.form.get("respuesta_texto")
        decision_boton = request.form.get("decision")

        # Validacion del boton y asignas el nuevo estatus
        if decision_boton == "APROBADO":
            id_nuevo_estatus = 6
            mensaje = "Solicitud aprobada exitosamente"
            tipo = "success"
        else:
            id_nuevo_estatus = 5
            mensaje = "Solicitud rechazada exitosamente"
            tipo = "danger"

        # Guardar los cambios en la bd
        registrar_respuesta_peticion_db(
            id_peticion=id_peticion,
            texto_respuesta=texto_respuesta,
            id_estatus_final=id_nuevo_estatus,
        )
        flash(mensaje, tipo)
        return redirect(url_for("oficios.panel_control"))

    # Si es GET
    return render_template(
        "oficios/responder_peticion_jud.html",
        peticion=info_peticion,
        archivos=archivos_peticion,
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
