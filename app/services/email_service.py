from flask import current_app
from flask_mail import Message
from app import mail


def enviar_notificacion_de_nuevo_oficio(datos, correo_subdirector, correo_adicional):
    """
    Envía la notificación.
    """

    # 1. Validar y limpiar destinatarios
    destinatarios = [correo_subdirector]  # El subdirector siempre va

    # Solo agregamos el adicional si existe y no está vacío
    if correo_adicional and correo_adicional.strip():
        destinatarios.append(correo_adicional)

    # 2. Definimos el Asunto
    asunto = f"Nuevo Oficio Asignado: {datos['folio']}"

    # 3. Creamos el objeto Mensaje
    msg = Message(
        subject=asunto,
        sender=current_app.config["MAIL_USERNAME"],
        recipients=destinatarios,
    )

    # 4. Cuerpo del correo
    msg.body = f"""         
    Saludos,

    Se le ha asignado un nuevo oficio para su atención.

    DETALLES DEL OFICIO:
    --------------------------------------
    Folio:    {datos['folio']}
    Asunto:   {datos['asunto']}
    Área:     {datos['area']}
    --------------------------------------
    
    Ingrese al sistema para atenderlo.
    """

    # 5. Enviamos (Si falla aquí, lanzará una excepción que capturará la otra función)
    mail.send(msg)
    return True


