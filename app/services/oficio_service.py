import os
import uuid
import shutil
from werkzeug.utils import secure_filename
from flask import current_app
from datetime import datetime

# Importamos la excepción para detectar folios duplicados
from pymysql.err import IntegrityError
from app.db import obtener_conexion

# Importamos la herramienta para trabajar con el pdf
from app.utils.pdf_tools import estampar_acuse_en_disco


# Importamos los modelos (Los "Empleados" que escriben en la BD)
from app.models.oficio import (
    crear_oficio_db,
    guardar_documento_db,
    registrar_historial_db,
    actualizar_respuesta_oficio_db,
    eliminar_oficio_db,
    crear_peticion_db,
    guardar_archivo_peticion_db,
)
from app.models.usuario import obtener_subdirector_por_area
from app.models.catalogo import obtener_nombre_del_area
from app.services.email_service import enviar_notificacion_de_nuevo_oficio


# EXTENSIONES PERMITIDAS
EXTENSIONES_PERMITIDAS = {"pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png"}


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

                # GENERAR FOLIO CONSECUTIVO
                anio_actual = datetime.now().year
                folio_consecutivo = self._obtener_siguiente_folio(cursor, anio_actual)

                # Insertar el Oficio (Encabezado)
                # Preparamos el diccionario limpio para el modelo
                datos_oficio = {
                    "folio": folio_manual,
                    "folio_consecutivo": folio_consecutivo,
                    "asunto": formulario["asunto"],
                    "descripcion_solicitud": formulario["descripcion_solicitud"],
                    "id_creador": usuario_gestor.id,
                    "id_asignado": subdirector["id_usuario"],
                    "id_area": id_area,
                }
                # El modelo escribe en la tabla 'oficios' y nos devuelve el ID generado (ej: 45)
                id_oficio = crear_oficio_db(cursor, datos_oficio)

                # LISTA PARA LOS MULTIPLES ARCHIVOS ADJUNTOS
                rutas_para_correo = []

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

                    # Estampar acuse de recibido si el archivo es pdf
                    if nombre.lower().endswith(".pdf"):
                        # 1. Necesitamos la ruta completa y real en el disco duro del servidor
                        ruta_absoluta = os.path.join(
                            current_app.root_path, "static", ruta
                        )

                        # 2. Preparamos los textos que irán en el sello
                        persona_que_recibio = usuario_gestor.nombre_completo
                        fecha_recibido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        folio_del_sistema = folio_consecutivo

                        # 3. Mandamos llamar a la función que dibuja el sello y sobrescribe el archivo
                        exito_estampado = estampar_acuse_en_disco(
                            ruta_absoluta,
                            persona_que_recibio,
                            folio_del_sistema,
                            fecha_recibido,
                        )

                        if not exito_estampado:
                            # Opcional: Podrías hacer un current_app.logger.warning aquí
                            print(
                                "Advertencia: No se pudo estampar el acuse en el PDF."
                            )

                    # CALCULAR LAS RUTAS DE LOS ARCHIVOS
                    ruta_absoluta_principal = os.path.join(
                        current_app.root_path, "static", ruta
                    )
                    rutas_para_correo.append(ruta_absoluta_principal)

                    # Guardamos la ruta en la tabla 'documentos_oficio' usando el mismo cursor
                    guardar_documento_db(
                        cursor=cursor,
                        id_oficio=id_oficio,
                        id_usuario=usuario_gestor.id,
                        nombre_real=nombre,
                        ruta=ruta,
                        tipo="SOLICITUD",
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

                        # CALCULAR LAS RUTAS DE LOS ARCHIVOS
                        ruta_absoluta_anexo = os.path.join(
                            current_app.root_path, "static", ruta
                        )
                        rutas_para_correo.append(ruta_absoluta_anexo)

                        guardar_documento_db(
                            cursor=cursor,
                            id_oficio=id_oficio,
                            id_usuario=usuario_gestor.id,
                            nombre_real=nombre,
                            ruta=ruta,
                            tipo="ANEXO_SOLICITUD",
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
                # Obtener el nombre del area
                nombre_area = obtener_nombre_del_area(formulario["id_area"])

                # Preparamos los datos para el email
                datos_email = {
                    "folio": folio_manual,
                    "asunto": formulario["asunto"],
                    "area": nombre_area,
                }
                # Preparammos los correos
                correo_sub = subdirector["correo_electronico"]
                correo_adicional = formulario.get("correo_adicional")

                # MULTIPLES ARCHIVOS ADJUNTOS
                enviar_notificacion_de_nuevo_oficio(
                    datos_email,
                    correo_sub,
                    correo_adicional,
                    lista_archivos_adjuntos=rutas_para_correo,
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
            carpeta_destino = os.path.join(
                current_app.root_path, "static", "uploads", str(id_oficio)
            )
            if os.path.exists(carpeta_destino):
                shutil.rmtree(carpeta_destino)  # Borra carpeta y contenido

            conexion.commit()
            return True, "Oficio y archivos eliminados correctamente."
        except Exception as e:
            conexion.rollback()
            return False, f"Error al eliminar oficio: {str(e)}"

    def procesar_peticion_jud(self, formulario, archivo, usuario_jud):
        """
        Guarda una petición en la tabla 'peticiones' y su archivo en 'archivos_peticion'.
        """
        conexion = obtener_conexion()
        try:
            # 1. Obtener destinatario (Subdirector del área)
            subdirector = obtener_subdirector_por_area(usuario_jud.id_area)
            if not subdirector:
                return False, "No se encontró un Subdirector activo en tu área."

            conexion.begin()
            with conexion.cursor() as cursor:
                # 2. Insertar en tabla PETICIONES
                datos_peticion = {
                    "asunto": formulario["asunto"],
                    "folio": formulario["folio"].strip(),
                    "descripcion": formulario["descripcion_solicitud"],
                    "id_creador": usuario_jud.id,
                    "id_destinatario": subdirector["id_usuario"],
                }
                id_peticion = crear_peticion_db(cursor, datos_peticion)

                # 3. Guardar Archivo (Obligatorio)
                if archivo and archivo.filename != "":
                    if not self._archivo_es_permitido(archivo.filename):
                        raise Exception("El archivo debe ser PDF, DOC o Excel.")

                    # Guardamos físico (en carpeta separada 'peticiones')
                    ruta, nombre, ext = self._guardar_archivo_peticion_en_disco(
                        archivo, id_peticion
                    )

                    # Guardamos en tabla ARCHIVOS_PETICION
                    guardar_archivo_peticion_db(
                        cursor, id_peticion, usuario_jud.id, nombre, ruta, ext
                    )
                else:
                    raise Exception(
                        "Es obligatorio adjuntar el archivo de la petición."
                    )

            conexion.commit()
            return True, f"Petición {datos_peticion['folio']} enviada correctamente."

        except IntegrityError:
            conexion.rollback()
            return False, f"El folio '{formulario['folio']}' ya existe."
        except Exception as e:
            conexion.rollback()
            current_app.logger.error(f"Error en procesar_peticion_jud: {e}")
            return False, f"Error al procesar la petición: {str(e)}"

    def procesar_peticion_subdirector(self, formulario, archivo, usuario_subdirector):
        """Guarda una peticion del subdirector en la tabla 'peticiones' y su archivo en 'archivos_peticion'."""
        conexion = obtener_conexion()
        try:
            # Obtener gestor/es
            pass
        except IntegrityError:
            conexion.rollback()
            return False, f"El folio '{formulario['folio']}' ya existe."
        except Exception as e:
            conexion.rollback()
            current_app.logger.error(f"Error en procesar_peticion_subdirector: {e}")
            return False, f"Error al procesar la petición: {str(e)}"

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

    def _guardar_archivo_peticion_en_disco(self, archivo, id_peticion):
        """
        Guarda archivos de peticiones en 'static/uploads/peticiones/ID/'
        para evitar colisiones con los oficios normales.
        """
        nombre_seguro = secure_filename(archivo.filename)
        extension = nombre_seguro.split(".")[-1].lower() if "." in nombre_seguro else ""
        nombre_unico = f"{uuid.uuid4().hex[:8]}_{nombre_seguro}"

        # Carpeta diferenciada
        carpeta_destino = os.path.join(
            current_app.root_path, "static", "uploads", "peticiones", str(id_peticion)
        )
        os.makedirs(carpeta_destino, exist_ok=True)

        archivo.save(os.path.join(carpeta_destino, nombre_unico))

        ruta_bd = f"uploads/peticiones/{id_peticion}/{nombre_unico}"
        return ruta_bd, nombre_seguro, extension

    def _archivo_es_permitido(self, nombre_archivo):
        """Verifica si un archivo tiene una extensión permitida."""
        return (
            "." in nombre_archivo
            and nombre_archivo.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS
        )

    def _obtener_siguiente_folio(self, cursor, anio):
        """
        Incrementa el contador en la tbl folios_contador y devuelve el nuevo número de forma SEGURA.
        Maneja la concurrencia bloqueando la fila durante la actualización.
        """
        # A. INTENTAMOS ACTUALIZAR (Esto bloquea la fila momentáneamente)
        sql_update = """
            UPDATE folios_contador 
            SET ultimo_folio = ultimo_folio + 1 
            WHERE anio = %s
        """
        cursor.execute(sql_update, (anio,))

        # B. VERIFICAMOS SI EL AÑO EXISTÍA
        # Si es el primer oficio del año y no existe la fila, la creamos
        if cursor.rowcount == 0:
            # Iniciamos en 1
            sql_insert = (
                "INSERT INTO folios_contador (anio, ultimo_folio) VALUES (%s, 1)"
            )
            cursor.execute(sql_insert, (anio,))
            return 1

        # C. RECUPERAMOS EL NÚMERO QUE ACABAMOS DE GENERAR
        sql_select = "SELECT ultimo_folio FROM folios_contador WHERE anio = %s"
        cursor.execute(sql_select, (anio,))
        resultado = cursor.fetchone()

        return resultado["ultimo_folio"]
