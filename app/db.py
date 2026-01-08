# app/db.py
import pymysql
from flask import current_app, g


def obtener_conexion():
    """
    Crea una conexión nueva si no existe una en la 'bandeja' (g) actual.
    Si ya existe, devuelve la que está lista para usarse.
    """
    if "conexion_mysql" not in g:
        # No hay conexión en la bandeja, creamos una nueva
        g.conexion_mysql = pymysql.connect(
            host=current_app.config["MYSQL_HOST"],
            user=current_app.config["MYSQL_USER"],
            password=current_app.config["MYSQL_PASSWORD"],
            database=current_app.config["MYSQL_DB"],
            port=current_app.config["MYSQL_PORT"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )

    return g.conexion_mysql


def cerrar_conexion(e=None):
    """Saca la conexión de la bandeja y la cierra al terminar la petición."""
    conexion = g.pop("conexion_mysql", None)

    if conexion is not None:
        conexion.close()


def configurar_base_datos(app):
    """
    Le dice a Flask: "Cuando termines de atender a un usuario,
    ejecuta la función cerrar_conexion automáticamente".
    """
    app.teardown_appcontext(cerrar_conexion)
