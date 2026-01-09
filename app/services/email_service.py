from flask import current_app
from flask_mail import Message
from app import mail


def enviar_notificacion_de_nuevo_oficio(datos, correo_subdirector, correo_copia):
    """Envía el correo de notificación.
    Retorna: (True/False, Mensaje)"""
    # try:
    #     # 1. Definimos el asunto y al destinatario
    #     asunto =
    pass
