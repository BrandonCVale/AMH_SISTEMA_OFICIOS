import io
import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import black, blue
from pypdf import PdfReader, PdfWriter


def crear_sello_acuse(folio_texto, fecha_hora_texto):
    """Genera el sello visual en memoria."""
    # Cear un archivo virtual que vive en RAM
    packet = io.BytesIO()
    # Crear un lienzo tamano carta y guardalo en el archivo virtual packet
    c = canvas.Canvas(packet, pagesize=letter)

    # --- POSICIÓN DEL SELLO ---
    # Esquina superior derecha.
    x = 350
    y = 740

    # Dibujamos un marco (Opcional, para que parezca sello)
    c.setStrokeColor(blue)
    c.setLineWidth(1)
    c.rect(x - 10, y - 10, 230, 45, stroke=1, fill=0)

    # Textos del sello
    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y + 20, "ACUSE DE RECIBIDO - SISTEMA")

    c.setFillColor(black)
    c.setFont("Helvetica", 9)
    c.drawString(x, y + 5, f"Folio: {folio_texto}")
    c.drawString(x, y - 8, f"Recibido: {fecha_hora_texto}")

    c.save()
    packet.seek(0)
    return packet


def estampar_acuse_en_disco(ruta_fisica_pdf, folio_texto, fecha_hora_texto):
    """
    Lee el PDF del disco, le pega el sello y lo SOBRESCRIBE.
    """
    try:
        # 1. Generar el sello en memoria
        sello_io = crear_sello_acuse(folio_texto, fecha_hora_texto)
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
