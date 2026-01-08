# run.py
import os
from app import crear_aplicacion

# Si no definimos entorno, usamos la config por defecto
nombre_config = os.getenv("FLASK_ENV", "default")
app = crear_aplicacion(nombre_config)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
