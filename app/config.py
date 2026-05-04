import os
from dotenv import load_dotenv

# Cargar variables del archivo .env al entorno
load_dotenv()


class ConfiguracionBase:
    """Configuración fundacional compartida por todos los entornos."""

    SECRET_KEY = os.getenv("SECRET_KEY")

    # Configuracion MySQL
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DB = os.getenv("MYSQL_DB")
    MYSQL_PORT = int(os.getenv("DB_PORT", 3306))

    # Configuracion para envio de correos
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS") == "True"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")


class ConfiguracionDesarrollo(ConfiguracionBase):
    """
    Configuración específica para el entorno de desarrollo local.
    Habilita trazas de error y herramientas de depuración.
    """

    DEBUG = True


class ConfiguracionProduccion(ConfiguracionBase):
    """
    Configuración estricta para el servidor de producción.
    Desactiva explícitamente cualquier herramienta de depuración.
    """

    DEBUG = False


# Diccionario de enrutamiento de configuración consumido por __init__.py
config = {
    "desarrollo": ConfiguracionDesarrollo,
    "produccion": ConfiguracionProduccion,
    "default": ConfiguracionDesarrollo,
}
