"""
Punto de entrada para el servidor de desarrollo local.
Advertencia: No ejecutar este archivo en el entorno de producción.
"""

# run.py
import os
from app import crear_aplicacion

# Si no definimos entorno, usamos la config por defecto
nombre_configuracion = os.getenv("ENTORNO_APP", "desarrollo")
app = crear_aplicacion(nombre_configuracion)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
