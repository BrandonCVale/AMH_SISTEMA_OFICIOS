from werkzeug.security import check_password_hash
from app.models.usuario import buscar_usuario_por_email


class ServicioAutenticacion:

    def intentar_login(self, email, password_plano):
        """
        Retorna el objeto Usuario si las credenciales son válidas.
        Retorna None si fallan.
        """
        # 1. Buscamos si el correo existe
        usuario = buscar_usuario_por_email(email)

        if usuario is None:
            print(f"DEBUG: Usuario no encontrado o inactivo: {email}")
            return None

        # 2. Verificamos si la contraseña coincide con el hash
        # check_password_hash(hash_guardado, contraseña_escrita_por_usuario)
        if check_password_hash(usuario.contrasena_hash, password_plano):
            return usuario
        
        print(f"DEBUG: Contraseña incorrecta. Hash en BD: {usuario.contrasena_hash}")
        return None
