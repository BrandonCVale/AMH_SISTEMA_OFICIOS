from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from app.config import config
from app.db import configurar_base_datos
from flask_mail import Mail


mail = Mail()

# Inicializamos el gestor de login
login_manager = LoginManager()
login_manager.login_view = "auth.login"



def crear_aplicacion(nombre_configuracion="default"):
    app = Flask(__name__)
    app.config.from_object(config[nombre_configuracion])

    configurar_base_datos(app)

    # 1. Iniciamos Flask-Login y Flask_Mail
    login_manager.init_app(app)
    mail.init_app(app)


    # 2. Registramos el Blueprint de Auth, Oficios
    from app.routes.auth import bp_auth
    from app.routes.oficios import bp_oficios

    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_oficios)

    @app.route("/")
    def inicio():
        # Si el usuario YA entró, lo mandamos a su panel
        if current_user.is_authenticated:
            return redirect(url_for("oficios.panel_control"))
        # Si NO ha entrado, lo mandamos al login automáticamente
        else:
            return redirect(url_for("auth.login"))

    return app


# 3. Función clave: Flask-Login usa esto para recargar al usuario usando la cookie
@login_manager.user_loader  # <--- Flask-Login usa esto para "aprender" a buscar usuarios
def cargar_usuario(id_usuario):
    from app.models.usuario import buscar_usuario_por_id

    return buscar_usuario_por_id(id_usuario)
