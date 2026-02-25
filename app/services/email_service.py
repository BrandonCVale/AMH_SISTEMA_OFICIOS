import os
import mimetypes
from flask import current_app
from flask_mail import Message
from app import mail


def enviar_notificacion_de_nuevo_oficio(
    datos, correo_subdirector, correo_adicional, lista_archivos_adjuntos=None
):
    """
    Envía la notificación y envia los archivos adjuntos.
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
    A quien corresponda,

    Se le ha dado seguimiento a su solicitud.

    DETALLES DE LA SOLICITUD:
    --------------------------------------
    Folio:    {datos['folio']}
    Asunto:   {datos['asunto']}
    Área:     {datos['area']}
    --------------------------------------
    
    Ingrese al sistema para atenderlo.
    Adjunto a este correo encontrará el documento original sellado por el sistema.
    """

    if lista_archivos_adjuntos:
        for ruta_archivo in lista_archivos_adjuntos:
            # Verificamos que exista
            if os.path.exists(ruta_archivo):
                nombre_archivo = os.path.basename(ruta_archivo)

                # Extraemos el mimetype (tipo de archivo)
                # Un MIME type consta de dos partes: Tipo: categoría general del contenido y Subtipo: especifica el formato exacto dentro de esa categoría
                # Ej: image/png
                mime_type, _ = mimetypes.guess_type(ruta_archivo)

                if not mime_type:
                    # Tipo generico por si no lo reconoce
                    mime_type = "application/octet-stream"

                with open(ruta_archivo, "rb") as archivo:
                    msg.attach(
                        filename=nombre_archivo,
                        content_type=mime_type,
                        data=archivo.read(),
                    )

    # 6. Enviamos (Si falla aquí, lanzará una excepción que capturará la otra función)
    mail.send(msg)
    return True


def enviar_notificacion_oficio_turnado(datos, correo_jud, lista_rutas_adjuntos=None):
    """
    Envia una notificacion por correo al JUD con los archivos adjuntos.
    """
    asunto = f"Se te ha asignado un oficio para su atención: {datos['folio_interno']}"

    msg = Message(
        subject=asunto,
        sender=current_app.config["MAIL_USERNAME"],
        recipients=[correo_jud],
    )
    msg.body = f"""
        Saludos, 
        Te han turnado una solicitud para su atención y seguimiento.
        
        Detalles:
        Folio: {datos['folio_interno']}
        Asunto: {datos['asunto']}
        Descripcion de la solicitud: {datos['descripcion']}
        
                
        Adjunto a este correo encontrará la solicitud oficial (PDF) y sus anexos correspondientes.
        Ingrese al sistema para dar respuesta a esta solicitud.
        """

    # ARCHIVOS ADJUNTOS
    if lista_rutas_adjuntos:
        for ruta in lista_rutas_adjuntos:
            if os.path.exists(ruta):
                nombre_archivo = os.path.basename(ruta)
                mime_type, _ = mimetypes.guess_type(ruta)
                if not mime_type:
                    mime_type = "application/octet-stream"
                with open(ruta, "rb") as archivo:
                    msg.attach(
                        filename=nombre_archivo,
                        content_type=mime_type,
                        data=archivo.read(),
                    )
    mail.send(msg)
    return True
