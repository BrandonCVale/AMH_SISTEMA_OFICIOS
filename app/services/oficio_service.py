import os
import uuid
import shutil
from werkzeug.utils import secure_filename
from flask import current_app

# Importamos la excepción para detectar folios duplicados
from pymysql.err import IntegrityError
from app.db import obtener_conexion

# Importamos los modelos (Los "Empleados" que escriben en la BD)
from app.models.oficio import (
    crear_oficio_db,
    guardar_documento_db,
    registrar_historial_db,
    actualizar_respuesta_oficio_db,
    eliminar_oficio_db,
)
from app.models.usuario import obtener_subdirector_por_area

from app.services.email_service import enviar_notificacion_de_nuevo_oficio


# EXTENSIONES PERMITIDAS
EXTENSIONES_PERMITIDAS = {"pdf", "doc", "docx", "xls", "xlsx"}


class ServicioOficio:

    def procesar_nuevo_oficio(
        self, formulario, archivo_principal, lista_anexos, usuario_gestor
    ):
        """
        Recibe los datos crudos del controlador y orquesta el guardado.
        """
        conexion = obtener_conexion()

        try:
            # --- PASO 1: VALIDACIONES DE NEGOCIO ---
            id_area = formulario["id_area"]

            # Buscamos al destinatario (Subdirector) en la BD
            subdirector = obtener_subdirector_por_area(id_area)
            if not subdirector:
                return (
                    False,
                    "El área seleccionada no tiene un Subdirector activo asignado.",
                )

            # Limpiamos el folio manual (quitamos espacios extra)
            folio_manual = formulario["folio"].strip()

            # --- PASO 2: INICIAR TRANSACCIÓN (El "Lápiz Compartido") ---
            conexion.begin()

            with conexion.cursor() as cursor:

                # A. Insertar el Oficio (Encabezado)
                # Preparamos el diccionario limpio para el modelo
                datos_oficio = {
                    "folio": folio_manual,
                    "asunto": formulario["asunto"],
                    "descripcion_solicitud": formulario["descripcion_solicitud"],
                    "id_creador": usuario_gestor.id,
                    "id_asignado": subdirector["id_usuario"],
                    "id_area": id_area,
                }
                # El modelo escribe en la tabla 'oficios' y nos devuelve el ID generado (ej: 45)
                id_oficio = crear_oficio_db(cursor, datos_oficio)

                # B. Guardar Archivo Principal (Físico + BD)
                if archivo_principal:
                    # Validamos extensión antes de guardar
                    if not self._archivo_es_permitido(archivo_principal.filename):
                        # Forzamos rollback manual o lanzamos excepción para que el catch la capture
                        raise Exception(
                            f"El archivo principal '{archivo_principal.filename}' no tiene una extensión permitida."
                        )

                    # Guardamos en disco duro y obtenemos la ruta
                    ruta, nombre = self._guardar_archivo_en_disco(
                        archivo_principal, id_oficio
                    )
                    # Guardamos la ruta en la tabla 'documentos_oficio' usando el mismo cursor
                    guardar_documento_db(
                        cursor, id_oficio, usuario_gestor.id, nombre, ruta, "SOLICITUD"
                    )

                # C. Guardar Anexos (Físico + BD)
                for anexo in lista_anexos:
                    if anexo.filename != "":
                        if not self._archivo_es_permitido(anexo.filename):
                            # Nota: Podrías decidir ignorar el archivo o cancelar todo el proceso. Aquí cancelamos todo.
                            raise Exception(
                                f"El anexo '{anexo.filename}' no tiene una extensión permitida."
                            )

                        ruta, nombre = self._guardar_archivo_en_disco(anexo, id_oficio)
                        guardar_documento_db(
                            cursor,
                            id_oficio,
                            usuario_gestor.id,
                            nombre,
                            ruta,
                            "ANEXO_SOLICITUD",
                        )

                # D. Registrar Historial (Bitácora)
                registrar_historial_db(
                    cursor,
                    id_oficio,
                    usuario_gestor.id,
                    1,
                    "Oficio creado y turnado al Subdirector.",
                )

            # --- PASO 3: CONFIRMAR CAMBIOS (COMMIT) ---
            # Si llegamos aquí sin errores, guardamos todo permanentemente.
            conexion.commit()

            try:
                # Preparamos los datos para el email
                datos_email = {
                    "folio": folio_manual,
                    "asunto": formulario["asunto"],
                    "area": f"Area ID {formulario['id_area']}",
                }
                # Preparammos los correos
                correo_sub = subdirector["correo_electronico"]
                correo_adicional = formulario["correo_adicional"]

                # Lo enviamos con la funcion del service
                enviar_notificacion_de_nuevo_oficio(
                    datos_email, correo_sub, correo_adicional
                )

                return True, f"Oficio {folio_manual} creado y notificado correctamente."

            except Exception as e_mail:
                # Si falla el correo, NO hacemos rollback (el oficio ya se guardó y es válido)
                print(f"Oficio guardado pero falló el envío del mail: {e_mail}")
                return (
                    True,
                    f"Oficio creado (Advertencia: No se pudo enviar el correo, verifique configuración).",
                )

        except IntegrityError as e:
            conexion.rollback()  # ¡Deshacemos todo!
            # Error 1062 es el código de MySQL para "Duplicate entry" (Folio repetido)
            if e.args[0] == 1062:
                return (
                    False,
                    f"El Folio '{folio_manual}' ya existe en el sistema. Verifique sus datos.",
                )
            return False, "Error de integridad en la base de datos."

        except Exception as e:
            conexion.rollback()  # ¡Deshacemos todo!
            # Usamos el logger de Flask en lugar de print para entornos de producción
            current_app.logger.error(f"Error crítico en procesar_nuevo_oficio: {e}")
            return False, f"Error interno: {str(e)}"

    def procesar_respuesta_jud(self, id_oficio, id_usuario, texto_respuesta, archivo):
        """
        Procesa la respuesta de un JUD: guarda texto, archivo y actualiza estatus.
        """
        conexion = obtener_conexion()
        
        try:
            with conexion.cursor() as cursor:
                # 1. Actualizar el oficio (Texto y Estatus a Finalizado)
                actualizar_respuesta_oficio_db(cursor, id_oficio, texto_respuesta)

                # 2. Guardar Archivo de Respuesta (Si existe)
                if archivo and archivo.filename != "":
                    if not self._archivo_es_permitido(archivo.filename):
                        raise Exception(
                            f"El archivo '{archivo.filename}' no es válido."
                        )

                    # Reutilizamos tu lógica privada existente
                    ruta, nombre = self._guardar_archivo_en_disco(archivo, id_oficio)

                    # Reutilizamos la función del modelo que preguntaste
                    guardar_documento_db(
                        cursor, id_oficio, id_usuario, nombre, ruta, "RESPUESTA_OFICIAL"
                    )

                # 3. Historial
                registrar_historial_db(
                    cursor,
                    id_oficio,
                    id_usuario,
                    4,
                    "Oficio atendido y finalizado por el JUD.",
                )

            conexion.commit()
            return True, "Respuesta enviada correctamente."

        except Exception as e:
            conexion.rollback()
            current_app.logger.error(f"Error al responder oficio {id_oficio}: {e}")
            return False, f"Error al guardar respuesta: {str(e)}"

    def eliminar_oficio_total(self, id_oficio):
        """
        ADMIN: Elimina un oficio de la BD y borra su carpeta de archivos.
        """
        conexion = obtener_conexion()
        conexion.begin()
        try:
            with conexion.cursor() as cursor:
                # 1. Borrar de la BD
                eliminar_oficio_db(cursor, id_oficio)
            
            # 2. Borrar carpeta física (static/uploads/{id_oficio})
            carpeta_destino = os.path.join(current_app.root_path, "static", "uploads", str(id_oficio))
            if os.path.exists(carpeta_destino):
                shutil.rmtree(carpeta_destino) # Borra carpeta y contenido

            conexion.commit()
            return True, "Oficio y archivos eliminados correctamente."
        except Exception as e:
            conexion.rollback()
            return False, f"Error al eliminar oficio: {str(e)}"

    def _guardar_archivo_en_disco(self, archivo, id_oficio):
        """
        Método auxiliar privado. Solo se encarga de mover el archivo al disco duro.
        """
        nombre_seguro = secure_filename(archivo.filename)
        # Agregamos UUID para que "reporte.pdf" no sobrescriba a otro "reporte.pdf"
        nombre_unico = f"{uuid.uuid4().hex[:8]}_{nombre_seguro}"

        # Definimos la carpeta: static/uploads/ID_DEL_OFICIO/
        carpeta_destino = os.path.join(
            current_app.root_path, "static", "uploads", str(id_oficio)
        )
        os.makedirs(carpeta_destino, exist_ok=True)  # Crea la carpeta si no existe

        ruta_completa = os.path.join(carpeta_destino, nombre_unico)
        archivo.save(ruta_completa)  # <-- Aquí se guarda físicamente

        # Retornamos la ruta relativa para la BD (ej: uploads/45/uuid_archivo.pdf)
        ruta_bd = f"uploads/{id_oficio}/{nombre_unico}"
        return ruta_bd, nombre_seguro

    def _archivo_es_permitido(self, nombre_archivo):
        """Verifica si un archivo tiene una extensión permitida."""
        return (
            "." in nombre_archivo
            and nombre_archivo.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS
        )
