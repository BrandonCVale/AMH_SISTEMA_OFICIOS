from flask import current_app
from flask_mail import Message
from app import mail


def enviar_notificacion_de_nuevo_oficio(datos, correo_subdirector, correo_adicional):
    try:
            # 1. Definimos el Asunto
            asunto = f"Nuevo Oficio Asignado: {datos['folio']}"
            
            # 2. Definimos los Destinatarios (Lista)
            destinatarios = [correo_subdirector, correo_adicional]
            
            # 3. Creamos el objeto Mensaje
            msg = Message(
                subject=asunto,
                sender=current_app.config['MAIL_USERNAME'],
                recipients=destinatarios
            )
            
            # 4. Cuerpo del correo (Texto plano)
            msg.body = f"""         
            Saludos,

            Se le ha dado seguimiento a tu oficio.

            DETALLES DEL OFICIO:
            --------------------------------------
            Folio:    {datos['folio']}
            Asunto:   {datos['asunto']}
            Área:     {datos['area']}
            --------------------------------------
            """
            
            # 5. ¡Enviamos!
            mail.send(msg)
            return True, "Notificación enviada con éxito."

    except Exception as e:
        print(f"Error al enviar correo: {e}")
        # Retornamos True (no bloqueante) pero avisamos del error
        return False, f"Error enviando correo: {str(e)}"

