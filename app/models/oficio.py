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
        INSERT INTO oficios 
        (folio_interno, asunto, descripcion_solicitud, id_usuario_creador, 
         id_usuario_asignado, id_area_asignada, id_estatus_actual)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    cursor.execute(
        sql,
        (
            datos["folio"],
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
            o.folio_interno,
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
            o.folio_interno,
            o.asunto,
            o.texto_respuesta,
            o.fecha_respuesta,
            id_usuario_creador,
            o.fecha_creacion,
            o.id_usuario_asignado,
            o.id_estatus_actual,
            
            -- PASA LOS ID A VALORES
            u.nombre_completo AS destinatario, -- En lugar de id_usuario_asignado
            e.nombre AS estatus -- En lugar de id_estatus_actual
                
        FROM oficios o
        -- 1. UNIMOS CON USUARIOS PARA OBTENER U.NOMBRE_COMPLETO
        INNER JOIN usuarios u ON o.id_usuario_asignado = u.id_usuario
        
        -- 2 UNIMOS CON CAT_ESTATUS PARA OBTENER E.NOMBRE
        INNER JOIN cat_estatus e ON o.id_estatus_actual = e.id_estatus
        
        WHERE o.id_usuario_creador = %s
        ORDER BY o.fecha_creacion DESC;
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
            AND id_estatus_actual IN (1, 2, 3);
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


def obtener_kpis_subdirector(id_usuario):
    """Cuenta los oficios creados por el Subdirector para sus KPIs."""

    conexion = obtener_conexion()
    conteo_kpis = {"Recibidos": 0, "Por Asignar": 0, "En Proceso": 0}

    with conexion.cursor() as cursor:
        # 1. Recibidos
        sql_recibidos = """
        SELECT
            COUNT(*) AS recibidos
        FROM
            oficios
        WHERE
            id_usuario_asignado = %s;
        """
        cursor.execute(sql_recibidos, (id_usuario,))
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

        # 3. En Proceso
        sql_en_proceso = """
        SELECT
            COUNT(*) AS en_proceso
        FROM
            oficios
        WHERE
            id_usuario_asignado = %s
            AND id_estatus_actual = 2;
        """
        cursor.execute(sql_en_proceso, (id_usuario,))
        conteo_kpis["En Proceso"] = cursor.fetchone()["en_proceso"]

    return conteo_kpis


def obtener_kpis_jud(id_usuario):
    """Cuenta los oficios del JUD para sus KPIs."""
    conexion = obtener_conexion()
    conteo_kpis = {"Pendientes": 0, "Atendidos": 0}

    with conexion.cursor() as cursor:
        # 1. Pendientes
        sql_pendientes = """
        SELECT
            COUNT(*) AS pendientes
        FROM
            oficios o
        WHERE
            o.id_usuario_asignado = %s;
        """
        cursor.execute(sql_pendientes, (id_usuario,))
        conteo_kpis["Pendientes"] = cursor.fetchone()["pendientes"]

        # 2. Atendidos
        sql_atendidos = """
        
        """

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
        o.fecha_creacion ASC;
    """

    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_usuario,))
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
                p.respuesta_subdirector
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
