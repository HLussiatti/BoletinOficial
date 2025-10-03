# Load Libraries
import requests
from bs4 import BeautifulSoup
from html import unescape
import pandas as pd
import logging
import base64
import re
import os

def descargar_pdf(link, referencia, output_dir="pdfs"):
    """
    Descarga el PDF desde un link del Boletín Oficial, solo si no existe.
    Maneja correctamente la URL de redirección para obtener el archivo PDF real.
    """
    try: 

        # Extraer tipo, número y fecha desde el link
        partes = link.strip().split('/')
        seccion = partes[-3]
        id_aviso = partes[-2]
        fecha_publicacion = partes[-1].split('?')[0]

        # Nombre de archivo y ruta completa
        #resolucion = re.sub(r'[\\/*?:"<>|]', "_", resolucion) -- ELIMINAR
        file_name = f"{referencia}_{fecha_publicacion}.pdf"
        ruta_completa = os.path.join(output_dir, file_name)

        # Saltear si ya existe
        if os.path.exists(ruta_completa):
            logging.info(f"Ya existe: {ruta_completa}")
            return ruta_completa


        # Endpoint de descarga
        url_pdf = "https://www.boletinoficial.gob.ar/pdf/download_aviso"

        # Headers HTTP
        headers = {
            "Referer": f"https://www.boletinoficial.gob.ar/detalleAviso/{seccion}/{id_aviso}/{fecha_publicacion}",
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # Payload POST
        data = {
            "nombreSeccion": seccion,
            "idAviso": id_aviso,
            "fechaPublicacion": fecha_publicacion
        }

        # Crear directorio si no existe
        os.makedirs(output_dir, exist_ok=True)

        # Hacer el request
        response = requests.post(url_pdf, headers=headers, data=data)

        if response.status_code == 200:
            json_data = response.json()
            pdf_base64 = json_data.get("pdfBase64")

            if pdf_base64:
                pdf_bytes = base64.b64decode(pdf_base64)
                with open(ruta_completa, "wb") as f:
                    f.write(pdf_bytes)
                logging.info(f"PDF descargado: {ruta_completa}")
                return ruta_completa
            else:
                logging.warning(f"No se encontró contenido PDF para: {file_name}")
                return None
        else:
            logging.error(f"Error HTTP {response.status_code} para {file_name}")
            return None

    except Exception as e:
        logging.error(f"Error al descargar {file_name}: {e}")
        return None