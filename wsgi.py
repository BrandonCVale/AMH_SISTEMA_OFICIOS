"""
Punto de entrada WSGI para el servidor de producción.
"""

import os
from app import crear_aplicacion

# Se fuerza la configuración de producción como mecanismo de seguridad por defecto
nombre_configuracion = os.getenv("ENTORNO_APP", "produccion")
aplicacion_flask = crear_aplicacion(nombre_configuracion)
