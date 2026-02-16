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


def obtener_nombre_del_area(id_area):
    """Regresa el nomnre del area en lugar de su id"""
    conexion = obtener_conexion()
    sql = """
        SELECT
            ca. nombre
        FROM
            cat_areas ca
        WHERE
            ca.id_area = %s;
    """

    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_area,))
        resultado = cursor.fetchone()
    if resultado:
        return resultado["nombre"]
    return "Area desconocida"
