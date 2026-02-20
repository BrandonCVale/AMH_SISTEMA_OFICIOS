import io
import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import black, blue
from pypdf import PdfReader, PdfWriter


def crear_sello_acuse(persona_recibe_doc, folio_consecutivo, fecha_hora):
    """Genera el sello visual en memoria."""
    # Cear un archivo virtual que vive en RAM
    packet = io.BytesIO()
    # Crear un lienzo tamano carta y guardalo en el archivo virtual packet
    c = canvas.Canvas(packet, pagesize=letter)

    # --- POSICIÓN DEL SELLO ---
    # Esquina superior derecha.
    x = 50
    y = 750

    # Dibujamos un marco (Opcional, para que parezca sello)
    c.setStrokeColor(blue)
    c.setLineWidth(1)
    c.rect(x - 10, y - 10, 260, 45, stroke=1, fill=0)

    # Textos del sello
    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(x, y + 20, "ACUSE DE RECIBIDO - SISTEMA")
    
    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y + 10, f"Persona que recibe: {persona_recibe_doc}")


    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y + 5, f"Folio: {folio_consecutivo}")
    c.drawString(x, y - 8, f"Fecha recibido: {fecha_hora}")

    c.save()
    packet.seek(0)
    return packet


def estampar_acuse_en_disco(ruta_fisica_pdf, persona, folio, fecha_hora):
    """
    Lee el PDF del disco, le pega el sello y lo SOBRESCRIBE.
    """
    try:
        # 1. Generar el sello en memoria
        sello_io = crear_sello_acuse(persona, folio, fecha_hora)
        sello_reader = PdfReader(sello_io)
        pagina_sello = sello_reader.pages[0]

        # 2. Leer el PDF original que el usuario acaba de subir
        reader = PdfReader(ruta_fisica_pdf)
        writer = PdfWriter()

        # 3. Fusionar el sello con la PRIMERA página
        if len(reader.pages) > 0:
            primera_pagina = reader.pages[0]
            primera_pagina.merge_page(pagina_sello)
            writer.add_page(primera_pagina)

            # Agregar el resto de las páginas intactas
            for i in range(1, len(reader.pages)):
                writer.add_page(reader.pages[i])

        # 4. Sobrescribir el archivo original en el disco
        with open(ruta_fisica_pdf, "wb") as f_out:
            writer.write(f_out)

        return True
    except Exception as e:
        print(f"Error al estampar el PDF: {e}")
        return False
