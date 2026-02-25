from typing import Optional
from flask_login import UserMixin
from app.db import obtener_conexion
from werkzeug.security import generate_password_hash


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

    @property
    def es_administrador(self):
        # Retorna True si el id_rol es 4
        return self.id_rol == 4


# ---- INICIO DE FUNCIONES DE ADMINISTRADOR ----
def crear_nuevo_usuario(datos):
    """Funcion de administrador para insertar un nuevo usuario en la DB"""
    conexion = obtener_conexion()

    # Hashear la contrasena
    hasheo = generate_password_hash(datos["contrasena_hash"])

    sql = """
    INSERT INTO usuarios
	(nombre_completo, correo_electronico, contrasena_hash, puesto, id_rol, id_area, activo)
    VALUES (%s, %s, %s, %s, %s, %s, 1);
    """
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                sql,
                (
                    datos["nombre_completo"],
                    datos["correo_electronico"],
                    hasheo,
                    datos["puesto"],
                    datos["id_rol"],
                    datos["id_area"],
                ),
            )
        conexion.commit()
        return True
    except Exception as e:
        print(f"Error al crear un nuevo usuario: {e}")
        conexion.rollback()
        return False


def eliminar_usuario(id_usuario):
    """Funcion de administrador para eliminar un usuario en la DB
    Desactiva un usuario (Soft Delete) para no romper historiales"""
    conexion = obtener_conexion()
    sql = "UPDATE usuarios SET activo = 0 WHERE id_usuario = %s"
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql, (id_usuario,))
        conexion.commit()
        return True
    except Exception:
        conexion.rollback()
        return False


def obtener_todos_los_usuarios():
    """Funcion de administrador para obtener a los usuarios activos y mostrarlos en la tabla"""
    conexion = obtener_conexion()
    sql = """
    SELECT
        u.id_usuario ,
        u.nombre_completo ,
        u.correo_electronico,
        u.puesto ,
        cr.nombre AS rol,
        ca.nombre AS area
    FROM
        usuarios u
    JOIN cat_roles cr ON
        u.id_rol = cr.id_rol
    JOIN cat_areas ca ON
        u.id_area = ca.id_area
    WHERE
        u.activo = 1;
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


def obtener_roles():
    """Obtiene todos los roles existentes en la BD"""
    conexion = obtener_conexion()
    sql = """
    SELECT
        id_rol,
        nombre
    FROM
        cat_roles;
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


def obtener_areas():
    """Obtiene todas las áreas existentes en la BD"""
    conexion = obtener_conexion()
    sql = """
    SELECT
        id_area,
        nombre
    FROM
        cat_areas;
    """
    with conexion.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


# ---- FIN DE FUNCIONES DE ADMINISTRADOR ----


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
        SELECT 
            id_usuario,
            nombre_completo,
            correo_electronico,
            id_rol,
            contrasena_hash,
            id_area 
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
        u.puesto,
        u.activo
    FROM
        usuarios u
    WHERE
        u.id_rol = 3
        AND u.activo = 1
        AND u.id_area = %s;
    """
    with conn.cursor() as cursor:
        cursor.execute(sql, (id_area,))
        return cursor.fetchall()
