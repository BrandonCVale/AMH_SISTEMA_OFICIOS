from flask import Flask
from flask_login import LoginManager
from app.config import config
from app.db import configurar_base_datos
from flask_mail import Mail

mail = Mail()

# Inicializamos el gestor de login
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def crear_aplicacion(nombre_configuracion: str = "default"):
    """
    Ensambla y retorna una instancia de la aplicación Flask.
    """

    app = Flask(__name__)

    clase_configuracion = config.get(nombre_configuracion, config["default"])
    app.config.from_object(clase_configuracion)

    configurar_base_datos(app)

    # 1. Iniciamos Flask-Login y Flask_Mail
    login_manager.init_app(app)
    mail.init_app(app)

    # 2. Registramos el Blueprint de Auth, Oficios
    from app.routes.main import bp_main
    from app.routes.auth import bp_auth
    from app.routes.oficios import bp_oficios
    from app.routes.admin import bp_admin

    app.register_blueprint(bp_main)
    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_oficios)
    app.register_blueprint(bp_admin)

    return app


# 3. Función clave: Flask-Login usa esto para recargar al usuario usando la cookie
@login_manager.user_loader  # <--- Flask-Login usa esto para "aprender" a buscar usuarios
def cargar_usuario(id_usuario):
    from app.models.usuario import buscar_usuario_por_id

    return buscar_usuario_por_id(id_usuario)
