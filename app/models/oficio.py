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



