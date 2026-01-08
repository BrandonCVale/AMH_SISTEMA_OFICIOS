from app.db import obtener_conexion


def obtener_areas_activas():
    """
    Recupera todas las áreas disponibles para enviar oficios.
    Retorna una lista de diccionarios: [{'id_area': 1, 'nombre': 'Recursos Humanos'}, ...]
    """
    conexion = obtener_conexion()
    sql = "SELECT id_area, nombre FROM cat_areas WHERE activo = 1 ORDER BY nombre ASC"

    with conexion.cursor() as cursor:
        cursor.execute(sql)
        # Como usamos DictCursor que esta definido desde el codigo de obtener_conexion(),
        # esto devuelve una lista de diccionarios
        datos = cursor.fetchall()
        return datos
