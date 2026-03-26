import os
import mimetypes
from flask import current_app, flash
from flask_mail import Message
from app import mail
from flask_login import current_user, login_required


def enviar_notificacion_de_nuevo_oficio(
    datos, correo_subdirector, lista_archivos_adjuntos=None
):
    """
    Envía una notificación por correo al subdirector cuando se crea un oficio.
    Se envia la informacion del oficio y sus archivos adjuntos.
    """

    # 1. Validar y limpiar destinatarios
    destinatarios = [correo_subdirector]  # El subdirector siempre va

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
    Te han asignado un nuevo oficio. Ingresa al sistema para atenderlo.

    DETALLES:
    
    Folio:    {datos['folio']}
    Asunto:   {datos['asunto']}
    Área:     {datos['area']}
    Cuerpo:   {datos['descripcion']}
    
    Adjunto a este correo encontrará el documento original sellado por el sistema y sus anexos.
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


def enviar_notificacion_correo_externo(
    datos, correo_solicitante, lista_archivos_adjuntos=None
):
    """
    Envia un mail al correo del solicitante que adjunten.
    Se envia informacion de la solicitud y archivos.
    """
    asunto = f"AMH - SEGUIMIENTO DE SOLICITUD"

    msg = Message(
        subject=asunto,
        sender=current_app.config["MAIL_USERNAME"],
        recipients=[correo_solicitante],
    )

    msg.body = f"""
    A quien corresponda,
    
    Se le ha dado seguimiento a su solicitud.
    
    DETALLES:
    
    Folio:    {datos['folio']}
    Asunto:   {datos['asunto']}
    Área:     {datos['area']}
    
    Adjunto a este correo encontrará el documento original sellado por el sistema."""

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

    mail.send(msg)
    return True


def enviar_notificacion_oficio_turnado(datos, correo_jud, lista_rutas_adjuntos=None):
    """
    Envía una notificación por correo al JUD con los archivos adjuntos.
    """
    asunto = f"Se te ha asignado un oficio para su atención: {datos['folio_interno']}"

    msg = Message(
        subject=asunto,
        sender=current_app.config["MAIL_USERNAME"],
        recipients=[correo_jud],
    )
    msg.body = f"""
        Saludos, 
        Se te ha turnado una solicitud para su atención y seguimiento.
        
        DETALLES:
        
        Folio: {datos['folio_interno']}
        Asunto: {datos['asunto']}
        Instrucciones del subdirector: {datos['instrucciones_subdirector']}
        
                
        Adjunto a este correo encontrará la solicitud oficial (PDF) SELLADA por el sistema y sus anexos correspondientes.
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


def enviar_notificacion_peticion_jud(
    datos, correo_subdirector, lista_archivos_adjuntos=None
):
    """Envía una notificación por correo al subdirector de un JUD con los archivos adjuntos."""
    asunto = f"Nueva petición de JUD: {datos['folio_interno']}"

    msg = Message(
        subject=asunto,
        sender=current_app.config["MAIL_USERNAME"],
        recipients=[correo_subdirector],
    )

    msg.body = f"""
    Un JUD te ha realizado una nueva petición, 
        
    DETALLES:
    
        Folio: {datos['folio_interno']}
        Asunto: {datos['asunto']}
        Cuerpo: {datos['descripcion']}
        
    Adjunto a este correo encontrará la solicitud en PDF.
        
    Ingrese al sistema para dar respuesta a esta petición.
    """

    # ARCHIVOS ADJUNTOS
    if lista_archivos_adjuntos:
        for ruta_relativa in lista_archivos_adjuntos:
            # 1. Armamos la ruta real y completa hacia tu carpeta static
            ruta_absoluta = os.path.join(current_app.static_folder, ruta_relativa)

            # 2. Imprimimos para asegurarnos de dónde lo está buscando (Ver terminal)
            print(f"Intentando adjuntar archivo desde: {ruta_absoluta}")

            if os.path.exists(ruta_absoluta):
                nombre_archivo = os.path.basename(ruta_absoluta)
                mime_type, _ = mimetypes.guess_type(ruta_absoluta)

                if not mime_type:
                    mime_type = "application/octet-stream"

                with open(ruta_absoluta, "rb") as archivo:
                    msg.attach(
                        filename=nombre_archivo,
                        content_type=mime_type,
                        data=archivo.read(),
                    )
                print("¡Archivo adjuntado con éxito!")
            else:
                # 3. Si falla
                print(
                    f"ERROR: No se encontró el archivo físico en la ruta: {ruta_absoluta}"
                )
    mail.send(msg)
    return True


def enviar_notificacion_peticion_subdirector(
    datos, correo_gestor, lista_archivos_adjuntos=None
):
    """
    Envia una notificacion por correo al gestor cuando el subdirector realiza una peticion.
    """

    asunto = f"Nueva peticion realizada por un subdirector: {datos['folio_interno']}"

    msg = Message(
        subject=asunto,
        sender=current_app.config["MAIL_USERNAME"],
        recipients=[correo_gestor],
    )

    msg.body = f"""
    Un subdirector te ha realizado una nueva petición, 
    
    DETALLES:
    
        Folio: {datos['folio_interno']}
        Asunto: {datos['asunto']}
        Cuerpo: {datos['descripcion']}
        
        
    Adjunto a este correo encontrarás la solicitud en formato PDF.
    
    Ingrese al sistema para dar respuesta a esta petición.
    """

    # ARCHIVOS ADJUNTOS
    if lista_archivos_adjuntos:
        for ruta_relativa in lista_archivos_adjuntos:
            # 1. Armamos la ruta real y completa hacia tu carpeta static
            ruta_absoluta = os.path.join(current_app.static_folder, ruta_relativa)

            # 2. Imprimimos para asegurarnos de dónde lo está buscando
            print(f"Intentando adjuntar archivo desde: {ruta_absoluta}")

            if os.path.exists(ruta_absoluta):
                nombre_archivo = os.path.basename(ruta_absoluta)
                mime_type, _ = mimetypes.guess_type(ruta_absoluta)

                if not mime_type:
                    mime_type = "application/octet-stream"

                with open(ruta_absoluta, "rb") as archivo:
                    msg.attach(
                        filename=nombre_archivo,
                        content_type=mime_type,
                        data=archivo.read(),
                    )
                print("¡Archivo adjuntado con éxito!")
            else:
                # 3. Si falla
                print(
                    f"ERROR: No se encontró el archivo físico en la ruta: {ruta_absoluta}"
                )
    mail.send(msg)
    return True
