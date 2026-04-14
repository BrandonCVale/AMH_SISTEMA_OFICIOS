from app.db import obtener_conexion


"""
NOTA SOBRE EL USO DE 'CURSOR':
Estas funciones reciben el objeto 'cursor' como parámetro para garantizar la INTEGRIDAD TRANSACCIONAL.
Esto permite que el controlador (ruta/servicio) ejecute varias inserciones (oficio, documento, historial)
dentro de una misma transacción.

- Si todo sale bien: Se hace un solo commit() al final.
- Si algo falla: Se hace rollback() y no se guarda nada (evitando datos corruptos).
"""


def crear_oficio_db(cursor, datos):
    """
    Inserta el encabezado del oficio en la tabla 'oficios'.
    """
    sql = """
        INSERT INTO oficios (
            folio_interno,
            folio_consecutivo,
            asunto,
            descripcion_solicitud,
            id_usuario_creador, 
            id_usuario_asignado,
            id_area_asignada,
            id_estatus_actual
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    cursor.execute(
        sql,
        (
            datos["folio"],
            datos["folio_consecutivo"],
            datos["asunto"],
            datos["descripcion_solicitud"],
            datos["id_creador"],
            datos["id_asignado"],
            datos["id_area"],
            1,
        ),
    )
    return cursor.lastrowid


def guardar_documento_db(cursor, id_oficio, id_usuario, nombre_real, ruta, tipo):
    """
    Inserta el registro del archivo en 'documentos_oficio'
    Nota: 'tipo' debe ser uno de los valores del ENUM actualizado.
    Nota: esta función no guarda el archivo físico (como el PDF o Word) en la base de datos, eso lo hace service.
    """
    # Extraemos extensión (ej: 'pdf')
    extension = nombre_real.split(".")[-1].lower() if "." in nombre_real else ""

    sql = """
        INSERT INTO documentos_oficio
        (id_oficio, id_usuario_subio, nombre_archivo_original, ruta_almacenamiento, extension, tipo_documento)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (id_oficio, id_usuario, nombre_real, ruta, extension, tipo))


def marcar_oficio_como_visto(id_oficio, id_usuario):
    """
    Registra la fecha y hora en que el usuario responsable abrió el oficio.
    """
    conexion = obtener_conexion()
    sql = """
        UPDATE oficios 
        SET fecha_lectura = NOW() 
        WHERE id_oficio = %s 
          AND id_usuario_asignado = %s 
          AND fecha_lectura IS NULL;
    """
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql, (id_oficio, id_usuario))
        conexion.commit()
    except Exception as e:
        print(f"Error al marcar un oficio como visto: {e}")


def registrar_historial_db(cursor, id_oficio, id_usuario, id_estatus_nuevo, comentario):
    """
    Inserta en 'historial_oficios'.
    """
    sql = """
        INSERT INTO historial_oficios
        (id_oficio, id_usuario_accion, id_estatus_nuevo, comentarios, fecha_movimiento)
        VALUES (%s, %s, %s, %s, NOW())
    """
    cursor.execute(sql, (id_oficio, id_usuario, id_estatus_nuevo, comentario))


def obtener_documentos_de_un_oficio(id_oficio):
    """Recupera todos los documentos de un oficio"""
    conexion = obtener_conexion()

    sql = """
        SELECT
            id_usuario_subio,
            nombre_archivo_original,
            ruta_almacenamiento,
            tipo_documento,
            fecha_subida
            
        FROM documentos_oficio
        WHERE id_oficio = %s
        ORDER BY nombre_archivo_original DESC;
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_oficio,))
        return cursor.fetchall()


def obtenter_los_detalles_de_un_oficio(id_oficio):
    """Recupera todos los detalles de informacion de un oficio"""
    conexion = obtener_conexion()

    sql = """
        SELECT
            o.id_oficio,
            o.fecha_creacion,
            ur.nombre_completo AS remitente,
            ur.correo_electronico AS correo_remitente,
            o.folio_interno,
            o.folio_consecutivo,
            o.asunto,
            o.descripcion_solicitud,
            o.fecha_respuesta,
            o.texto_respuesta,
            o.fecha_recepcion ,
            o.fecha_lectura,
            o.instrucciones_subdirector,
            -- SELECT DE LOS JOINS
            ud.nombre_completo AS destinatario,
            ce.nombre AS estatus
        FROM
            oficios o
        JOIN usuarios ur ON
            o.id_usuario_creador = ur.id_usuario
        JOIN usuarios ud ON
            o.id_usuario_asignado = ud.id_usuario
        JOIN cat_estatus ce ON
            o.id_estatus_actual = ce.id_estatus
        WHERE
            o.id_oficio = %s;
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_oficio,))
        return cursor.fetchone()


def obtener_historial_de_un_oficio(id_oficio):
    """Recupera el historial de movimientos de un oficio"""
    conexion = obtener_conexion()

    sql = """
        SELECT
            h.id_historial,
            h.id_oficio,
            u.nombre_completo AS usuario_accion,
            ce.nombre AS nuevo_estatus,
            ce2.nombre AS estatus_anterior,
            h.fecha_movimiento
        FROM
            historial_oficios h
        JOIN usuarios u ON
            h.id_usuario_accion = u.id_usuario
        JOIN cat_estatus ce ON
            ce.id_estatus = h.id_estatus_nuevo
        LEFT JOIN cat_estatus ce2 ON
            ce2.id_estatus = h.id_estatus_anterior
        WHERE
            h.id_oficio = %s
        ORDER BY h.fecha_movimiento DESC;
    """

    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_oficio,))
        return cursor.fetchall()


# MODELS QUE USA EL GESTOR
# -- AQUI EMPIEZA
def obtener_oficios_del_gestor(id_usuario_gestor):
    """Recupera todos los oficios creados por un usuario gestor"""
    conexion = obtener_conexion()

    sql = """
        SELECT
            o.id_oficio,
            o.folio_consecutivo,
            o.folio_interno,
            o.asunto,
            o.texto_respuesta,
            o.fecha_respuesta,
            id_usuario_creador,
            o.fecha_creacion,
            o.id_usuario_asignado,
            o.id_estatus_actual,
            -- PASA LOS ID A VALORES
            u.nombre_completo AS destinatario,
            -- En lugar de id_usuario_asignado
            e.nombre AS estatus,
            -- En lugar de id_estatus_actual
            ca.nombre AS area_destinataria
        FROM
            oficios o
            -- 1. UNIMOS CON USUARIOS PARA OBTENER U.NOMBRE_COMPLETO
        INNER JOIN usuarios u ON
            o.id_usuario_asignado = u.id_usuario
            -- 2 UNIMOS CON CAT_ESTATUS PARA OBTENER E.NOMBRE
        INNER JOIN cat_estatus e ON
            o.id_estatus_actual = e.id_estatus
        INNER JOIN cat_areas ca ON
            o.id_area_asignada = ca.id_area
        WHERE
            o.id_usuario_creador = %s
        ORDER BY
            o.fecha_creacion DESC;
    """

    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_usuario_gestor,))
        return cursor.fetchall()


def obtener_kpis_gestor(id_usuario):
    """Cuenta los oficios creados por el Gestor para sus KPIs."""

    conexion = obtener_conexion()
    conteo_kpis = {"Enviados": 0, "En Revisión": 0, "Finalizados": 0}

    with conexion.cursor() as cursor:
        # 1. Total de enviados
        sql_enviados = """
        SELECT
            COUNT(*) AS total_enviados
        FROM
            oficios
        WHERE
            id_usuario_creador = %s;
        """
        cursor.execute(sql_enviados, (id_usuario,))
        conteo_kpis["Enviados"] = cursor.fetchone()["total_enviados"]

        # 2. En revision
        sql_en_revision = """
        SELECT
            COUNT(*) AS en_revision
        FROM
            oficios
        WHERE
            id_usuario_creador = %s
            AND id_estatus_actual IN (1, 3);
        """
        cursor.execute(sql_en_revision, (id_usuario,))
        conteo_kpis["En Revisión"] = cursor.fetchone()["en_revision"]

        # 3. Finalizados
        sql_finalizados = """
        SELECT
            COUNT(*) AS finalizados
        FROM
            oficios
        WHERE
            id_usuario_creador = %s
            AND id_estatus_actual = 4;
        """
        cursor.execute(sql_finalizados, (id_usuario,))
        conteo_kpis["Finalizados"] = cursor.fetchone()["finalizados"]

    return conteo_kpis


# -- AQUI TERMINA


def obtener_kpis_subdirector(id_usuario, id_area):
    """Cuenta los oficios creados por el Subdirector para sus KPIs."""

    conexion = obtener_conexion()
    conteo_kpis = {"Recibidos": 0, "Por Asignar": 0, "Peticiones": 0}

    with conexion.cursor() as cursor:
        # 1. Recibidos
        sql_recibidos = """
        SELECT
            COUNT(*) AS recibidos
        FROM
            oficios
        WHERE
            id_area_asignada = %s;
        """
        cursor.execute(sql_recibidos, (id_area,))
        conteo_kpis["Recibidos"] = cursor.fetchone()["recibidos"]

        # 2. Por asignar
        sql_por_asignar = """
        SELECT
            COUNT(*) AS por_asignar
        FROM
            oficios
        WHERE 
            id_usuario_asignado = %s
            AND id_estatus_actual = 1;
        """

        cursor.execute(sql_por_asignar, (id_usuario,))
        conteo_kpis["Por Asignar"] = cursor.fetchone()["por_asignar"]

        # 3. Peticiones juds
        sql_en_proceso = """
        SELECT
            COUNT(p.id_peticion) AS peticiones_juds
        FROM
            peticiones p
        WHERE
            p.id_destinatario = %s
            AND p.id_estatus = 1;
        """
        cursor.execute(sql_en_proceso, (id_usuario,))
        conteo_kpis["Peticiones"] = cursor.fetchone()["peticiones_juds"]

    return conteo_kpis


def obtener_kpis_jud(id_usuario):
    """Cuenta los oficios del JUD para sus KPIs."""
    conexion = obtener_conexion()
    conteo_kpis = {"Pendientes": 0, "Atendidos": 0, "Peticiones": 0}

    with conexion.cursor() as cursor:
        sql_asignaciones = """
        SELECT
            -- PENDIENTES
            SUM(CASE WHEN id_estatus_actual = 2 THEN 1 ELSE 0 END) AS pendientes,
            -- ATENDIDAS
            SUM(CASE WHEN id_estatus_actual IN (3, 4) THEN 1 ELSE 0 END) AS atendidos
        FROM
            oficios
        WHERE
            id_usuario_asignado = %s;
       """

        cursor.execute(sql_asignaciones, (id_usuario,))
        resultado_oficios = cursor.fetchone()
        conteo_kpis["Pendientes"] = int(resultado_oficios["pendientes"] or 0)
        conteo_kpis["Atendidos"] = int(resultado_oficios["atendidos"] or 0)

        sql_mis_peticiones = """
            SELECT COUNT(*) as peticiones
            FROM peticiones
            WHERE id_usuario_creador = %s;
        """
        cursor.execute(sql_mis_peticiones, (id_usuario,))
        resultado_peticiones = cursor.fetchone()
        conteo_kpis["Peticiones"] = int(resultado_peticiones["peticiones"] or 0)

    return conteo_kpis


def obtener_bandeja_entrada_subdirector(id_usuario):
    """
    Devuelve una lista de dccionarios con los oficios con estatus
    'EN REVISION' del area.
    """
    conexion = obtener_conexion()

    sql = """
    SELECT
        o.id_oficio,
        o.folio_consecutivo,
        u.nombre_completo AS remitente,
        o.fecha_creacion,
        o.folio_interno,
        o.asunto,
        o.descripcion_solicitud,
        e.nombre AS estatus
    FROM
        oficios o
    JOIN cat_estatus e ON
        o.id_estatus_actual = e.id_estatus
    JOIN usuarios u ON
        o.id_usuario_creador = u.id_usuario
    WHERE
        o.id_usuario_asignado = %s
        AND o.id_estatus_actual = 1
    ORDER BY
        o.fecha_creacion DESC;
    """

    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_usuario,))
        return cursor.fetchall()


def obtener_oficios_atendidos_del_subdirector(id_area):
    """
    Recupera los oficios del área que ya fueron procesados (Estatus != 1).
    Sirve para llenar la tabla de 'Asignaciones Atendidas' del Subdirector.
    """
    conexion = obtener_conexion()
    sql = """
    SELECT
        o.id_oficio,
        o.folio_consecutivo,
        o.folio_interno,
        o.asunto,
        ce.nombre AS estatus
    FROM
        oficios o
    JOIN cat_estatus ce ON
        o.id_estatus_actual = ce.id_estatus
    WHERE
        o.id_area_asignada = %s
        AND o.id_estatus_actual != 1
    ORDER BY
        o.fecha_creacion DESC;
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_area,))
        return cursor.fetchall()


def asignar_oficio_a_jud_db(id_oficio, id_jud, id_subdirector, instrucciones):
    """
    Asigna el oficio a un JUD, cambia el estatus a 'En Proceso' (2)
    y registra el historial.
    """
    conexion = obtener_conexion()
    conexion.begin()
    try:
        with conexion.cursor() as cursor:
            # 1. Actualizar el oficio
            sql_update = """
                UPDATE oficios 
                SET id_usuario_asignado = %s, 
                    id_estatus_actual = 2, 
                    fecha_lectura = NULL,
                    instrucciones_subdirector = %s
                WHERE id_oficio = %s
            """
            cursor.execute(sql_update, (id_jud, instrucciones, id_oficio))

            # 2. Registrar en el historial
            registrar_historial_db(
                cursor,
                id_oficio,
                id_subdirector,
                2,
                "Oficio asignado al JUD para su atención.",
            )

        conexion.commit()
        return True
    except Exception as e:
        print(f"Error al asignar oficio: {e}")
        conexion.rollback()
        return False


def obtener_oficios_asignados_a_un_jud(id_jud):
    """Recupera todos los oficios PENDIENTES asignados a un JUD"""
    conexion = obtener_conexion()

    sql_pendientes = """
        SELECT
            o.id_oficio ,
            o.folio_consecutivo ,
            o.folio_interno ,
            o.asunto ,
            o.descripcion_solicitud
        FROM
            oficios o
        WHERE
            o.id_usuario_asignado = %s
            AND o.fecha_respuesta IS NULL
        ORDER BY
            o.fecha_recepcion DESC;
    """

    with conexion.cursor() as cursor:
        cursor.execute(sql_pendientes, (id_jud,))
        return cursor.fetchall()


def oficios_atendidos_por_un_jud(id_jud):
    """Recupera todos los oficios ATENDIDOS por un JUD"""
    conexion = obtener_conexion()
    sql_atendidos = """
                SELECT
                    o.id_oficio ,
                    o.folio_consecutivo ,
                    o.folio_interno ,
                    o.asunto ,
                    o.descripcion_solicitud
                FROM
                    oficios o
                WHERE
                    o.id_usuario_asignado = %s
                    AND o.fecha_respuesta IS NOT NULL
                ORDER BY
                    o.fecha_recepcion DESC;
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql_atendidos, (id_jud,))
        return cursor.fetchall()


def actualizar_respuesta_oficio_db(cursor, id_oficio, texto_respuesta):
    """Actualiza el oficio con la respuesta del JUD y lo finaliza (Estatus 4)"""
    sql = """
        UPDATE oficios
        SET texto_respuesta = %s,
            fecha_respuesta = NOW(),
            id_estatus_actual = 4
        WHERE id_oficio = %s
    """
    cursor.execute(sql, (texto_respuesta, id_oficio))


# --- FUNCIONES PARA EL ADMINISTRADOR ---
def obtener_todos_los_oficios_admin():
    """Obtiene un resumen de todos los oficios para el panel de admin"""
    conexion = obtener_conexion()
    sql = """
        SELECT o.id_oficio, o.folio_interno, o.asunto, o.fecha_creacion, 
               ce.nombre as estatus, u.nombre_completo as creador
        FROM oficios o
        JOIN cat_estatus ce ON o.id_estatus_actual = ce.id_estatus
        JOIN usuarios u ON o.id_usuario_creador = u.id_usuario
        ORDER BY o.fecha_creacion DESC
        LIMIT 100; -- Limitamos a 100 para no saturar la vista
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


def eliminar_oficio_db(cursor, id_oficio):
    """
    Elimina físicamente el registro del oficio y sus dependencias.
    Se debe ejecutar dentro de una transacción.
    """
    # 1. Eliminar historial
    cursor.execute("DELETE FROM historial_oficios WHERE id_oficio = %s", (id_oficio,))
    # 2. Eliminar registros de documentos (los archivos físicos los borra el service)
    cursor.execute("DELETE FROM documentos_oficio WHERE id_oficio = %s", (id_oficio,))
    # 3. Eliminar el oficio
    cursor.execute("DELETE FROM oficios WHERE id_oficio = %s", (id_oficio,))


def crear_peticion_db(cursor, datos):
    """Inserta una nueva petición en la tabla 'peticiones'"""
    sql = """
        INSERT INTO peticiones
        (asunto, folio_peticion, descripcion, id_usuario_creador, id_destinatario, id_estatus)
        VALUES (%s, %s, %s, %s, %s, 1)
    """
    cursor.execute(
        sql,
        (
            datos["asunto"],
            datos["folio"],
            datos["descripcion"],
            datos["id_creador"],
            datos["id_destinatario"],
        ),
    )
    return cursor.lastrowid


def obtener_peticiones_del_jud(id_jud):
    """Retorna las peticiones hechas por un jud"""
    conexion = obtener_conexion()
    sql = """
            SELECT
                p.id_peticion,
                p.folio_peticion,
                p.asunto,
                p.descripcion,
                ce.nombre AS estatus,
                p.respuesta_recibida
            FROM
                peticiones p
            JOIN cat_estatus ce ON
                p.id_estatus = ce.id_estatus
            WHERE
                p.id_usuario_creador = %s
            ORDER BY
                p.fecha_creacion DESC;
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_jud,))
        return cursor.fetchall()

def obtener_peticiones_hechas_por_un_subdirector(id_subdirector):
    """Retorna las peticiones hechas por un subdirector"""
    conexion = obtener_conexion()
    sql = """
    SELECT
        p.id_peticion,
        p.folio_peticion,
        p.asunto,
        p.descripcion,
        ce.nombre AS estatus,
        p.respuesta_recibida
    FROM
        peticiones p
    JOIN cat_estatus ce ON
        p.id_estatus = ce.id_estatus
    WHERE
        p.id_usuario_creador = %s
    ORDER BY
        p.fecha_creacion DESC;
    """
    with conexion.cursor() as c:
        c.execute(sql, (id_subdirector,))
        return c.fetchall()


def obtener_solicitudes_de_mis_juds(id_subdirector):
    """Obtiene las peticiones hechas por un jud, que son asignadas a su subdirector.
    Lo usa el subdirector para la pestana solicitudes juds"""
    conexion = obtener_conexion()
    sql = """
            SELECT
                p.id_peticion,
                p.asunto ,
                p.folio_peticion ,
                p.descripcion ,
                u.nombre_completo AS remitente,
                p.fecha_creacion,
                ce.nombre AS estatus
            FROM
                peticiones p
            JOIN usuarios u ON
                p.id_usuario_creador = u.id_usuario
            JOIN cat_estatus ce ON 
                p.id_estatus = ce.id_estatus
            WHERE
                p.id_destinatario = %s
            ORDER BY
                p.fecha_creacion DESC;
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_subdirector,))
        return cursor.fetchall()


def obtener_solicitudes_de_mis_subdirectores(id_gestor):
    """Obtiene las peticiones hechas por los subdirectores en donde el usuario gestor
    es el asignado por el subdirector"""
    conexion = obtener_conexion()
    sql = """
        SELECT
            p.id_peticion,
            p.folio_peticion,
            p.asunto,
            p.descripcion,
            ce.nombre AS estatus,
            p.respuesta_recibida
        FROM
            peticiones p
        JOIN cat_estatus ce ON
            p.id_estatus = ce.id_estatus
        WHERE
            p.id_destinatario = %s
        ORDER BY 
            p.fecha_creacion DESC;
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_gestor,))
        return cursor.fetchall()


def obtener_detalles_peticion(id_peticion):
    """Obtiene los detalles de una peticion"""
    conexion = obtener_conexion()
    sql = """
        SELECT
            p.id_peticion ,
            p.respuesta_recibida ,
            p.folio_peticion ,
            u.nombre_completo AS solicitante,
            p.fecha_creacion ,
            p.asunto,
            p.descripcion,
            ce.nombre AS estatus,
            u2.nombre_completo AS destinatario
        FROM
            peticiones p
        JOIN usuarios u ON
            p.id_usuario_creador = u.id_usuario
        JOIN cat_estatus ce ON
            p.id_estatus = ce.id_estatus
        JOIN usuarios u2 ON
            p.id_destinatario = u2.id_usuario
        WHERE
            p.id_peticion = %s
        ORDER BY
            p.fecha_creacion DESC;
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_peticion,))
        return cursor.fetchone()


def obtener_archivos_peticion(id_peticion):
    """Obtiene los archivos de una peticion"""
    conexion = obtener_conexion()
    sql = """
            SELECT
                ap.id_documento ,
                ap.id_peticion ,
                ap.nombre_archivo ,
                ap.ruta_almacenamiento ,
                ap.extension,
                'SOLICITUD' as tipo_documento
            FROM
                archivos_peticion ap
            WHERE
                ap.id_peticion = %s;
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_peticion,))
        return cursor.fetchall()


def registrar_respuesta_peticion_db(id_peticion, texto_respuesta, id_estatus_final):
    """Guarda la respuesta del subdirector en la tabla 'peticiones' columna 'respuesta_subdirector'
    y define el estatus aprobatorio o rechazado"""
    conexion = obtener_conexion()
    sql = """
            UPDATE
                peticiones p
            SET
                p.respuesta_recibida = %s,
                p.id_estatus = %s
            WHERE
                p.id_peticion = %s;
    """
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql, (texto_respuesta, id_estatus_final, id_peticion))
            conexion.commit()
    except Exception as e:
        print(f"Error al actualizar petición: {e}")
        conexion.rollback()
        raise e


def guardar_archivo_peticion_db(
    cursor, id_peticion, id_usuario, nombre, ruta, extension
):
    """Inserta el registro del archivo en 'archivos_peticion'"""
    sql = """
        INSERT INTO archivos_peticion
        (id_peticion, id_usuario_creador, nombre_archivo, ruta_almacenamiento, extension)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (id_peticion, id_usuario, nombre, ruta, extension))


def obtener_a_todos_los_gestores():
    """Regresa una lista con todos los usuarios de tipo gestor"""
    conexion = obtener_conexion()

    sql = """
        SELECT
            id_usuario,
            nombre_completo,
            correo_electronico,
            activo
        FROM
            usuarios
        WHERE
            id_rol = 1;
    """

    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()
    except Exception as e:
        print(f"Error al obtener la lista de gestores: {e}")
        return None


def obtener_correo_usuario_por_id(id_usuario):
    """Obtiene el correo de un usuario basandose en su id.
    Ideal para el Gestor"""
    conexion = obtener_conexion()
    sql = """
    SELECT
        nombre_completo ,
        correo_electronico ,
        activo
    FROM
        usuarios
    WHERE
        id_usuario = %s;
    """
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql, (id_usuario,))
            return cursor.fetchall()
    except Exception as e:
        print(
            f"Error al intentar obtener el correo de un usuario por su iden funcion obtener_correo_usuario_por_id. Error: {e}"
        )
        return None


def obtener_correo_subdirector_por_area(id_area):
    conexion = obtener_conexion()
    sql = """
    SELECT
        u.correo_electronico
    FROM
        usuarios u
    WHERE
        u.id_area = %s
        AND u.id_rol = 2;
    """
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql, (id_area,))
            resultado = cursor.fetchone()
            
            if resultado: 
                return resultado['correo_electronico']
            return None

    except Exception as e:
        print(f"Error al obtener el correo del subdirector: {e}")
