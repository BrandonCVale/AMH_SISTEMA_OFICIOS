from typing import Optional
from flask_login import UserMixin
from app.db import obtener_conexion


class Usuario(UserMixin):
    """
    Estructura que Flask-Login necesita para saber quién está conectado.
    Va a la bd y trae los datos del usuario en crudo.
    """

    def __init__(
        self,
        id_usuario: int,
        nombre_completo: str,
        correo_electronico: str,
        id_rol: int,
        contrasena_hash: str,
        id_area: int,
    ):
        self.id = id_usuario  # Flask-Login exige que se llame 'id'
        self.nombre_completo = nombre_completo
        self.correo_electronico = correo_electronico
        self.id_rol = id_rol
        self.contrasena_hash = contrasena_hash
        self.id_area = id_area

    @property
    def es_gestor(self):
        # Retorna True si el id_rol es 1
        return self.id_rol == 1

    @property
    def es_subdirector(self):
        # Retorna True si el id_rol es 2
        return self.id_rol == 2

    @property
    def es_jud(self):
        # Retorna True si el id_rol es 3
        return self.id_rol == 3


def buscar_usuario_por_email(email: str) -> Optional[Usuario]:
    conexion = obtener_conexion()
    sql = """
        SELECT id_usuario, nombre_completo, correo_electronico, id_rol, contrasena_hash, id_area
        FROM usuarios 
        WHERE correo_electronico = %s AND activo = 1
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql, (email,))
        datos = cursor.fetchone()

        if datos:
            # Convertimos el diccionario de la BD a un objeto Usuario
            return Usuario(
                datos["id_usuario"],
                datos["nombre_completo"],
                datos["correo_electronico"],
                datos["id_rol"],
                datos["contrasena_hash"],
                datos["id_area"],
            )
    return None


def buscar_usuario_por_id(id_usuario: int) -> Optional[Usuario]:
    conexion = obtener_conexion()
    sql = """
        SELECT id_usuario, nombre_completo, correo_electronico, id_rol, contrasena_hash, id_area 
        FROM usuarios 
        WHERE id_usuario = %s AND activo = 1
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql, (id_usuario,))
        datos = cursor.fetchone()

        if datos:
            return Usuario(
                datos["id_usuario"],
                datos["nombre_completo"],
                datos["correo_electronico"],
                datos["id_rol"],
                datos["contrasena_hash"],
                datos["id_area"],
            )
    return None


def obtener_subdirector_por_area(id_area):
    """Busca al subdirector activo del área destino"""
    conn = obtener_conexion()
    sql = """
        SELECT id_usuario, nombre_completo, puesto, correo_electronico 
        FROM usuarios 
        WHERE id_area = %s AND id_rol = 2 AND activo = 1
        LIMIT 1
    """
    with conn.cursor() as cursor:
        cursor.execute(sql, (id_area,))
        return cursor.fetchone()


def obtener_juds_por_area(id_area):
    """Devuelve una lista de diccionarios con todos los usarios con rol jud,
    que pertenezcan a un area seleccionada."""

    conn = obtener_conexion()

    sql = """
    SELECT
        u.id_usuario,
        u.nombre_completo,
        u.correo_electronico,
        u.id_rol,
        u.id_area,
        u.activo
    FROM
        usuarios u
    WHERE
        (u.id_area = %s)
        AND u.id_rol = 3
        AND u.activo = 1
    ORDER BY
        u.nombre_completo ASC;
    """
    with conn.cursor() as cursor:
        cursor.execute(sql, (id_area,))
        return cursor.fetchall()
