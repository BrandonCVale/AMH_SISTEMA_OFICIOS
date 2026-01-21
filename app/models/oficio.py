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
            ur.nombre_completo AS remitente,
            o.folio_interno,
            o.asunto,
            o.descripcion_solicitud,
            o.fecha_respuesta,
            o.texto_respuesta,
            o.fecha_recepcion ,
            o.fecha_lectura,
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


def obtener_kpis_subdirector(id_area):
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
            id_area_asignada = %s
            AND id_estatus_actual = 1;
        """

        cursor.execute(sql_por_asignar, (id_area,))
        conteo_kpis["Por Asignar"] = cursor.fetchone()["por_asignar"]

        # 3. En Proceso
        sql_en_proceso = """
        SELECT
            COUNT(*) AS en_proceso
        FROM
            oficios
        WHERE
            id_area_asignada =%s
            AND id_estatus_actual = 2;
        """
        cursor.execute(sql_en_proceso, (id_area,))
        conteo_kpis["En Proceso"] = cursor.fetchone()["en_proceso"]

    return conteo_kpis


def obtener_bandeja_entrada_subdirector(id_area):
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
        o.id_area_asignada = %s
        AND o.id_estatus_actual = 1
    ORDER BY
        o.fecha_creacion ASC;
    """

    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_area,))
        return cursor.fetchall()
