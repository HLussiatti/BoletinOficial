import os
import requests
from bs4 import BeautifulSoup
import re

def obtener_detalles_aviso(url_detalle, resolucion):
    """Obtiene el título y texto de un aviso del Boletín Oficial y guarda el detalle en un .txt."""
    try:
        session = requests.Session()
        headers = {"User-Agent": "Mozilla/5.0"}
        response = session.get(url_detalle, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        titulo_tag = soup.find(id='tituloDetalleAviso')
        cuerpo_tag = soup.find(id='cuerpoDetalleAviso')

        titulo = titulo_tag.text.strip() if titulo_tag else "Sin título"
        cuerpo = cuerpo_tag.text.strip() if cuerpo_tag else "Sin texto"

        # Limpiar el título para que sea un nombre de archivo válido
        # titulo_limpio = re.sub(r'[\\/*?:"<>|]', "_", titulo)

        # Crear carpeta 'detalles' si no existe
        os.makedirs("detalles", exist_ok=True)

        # Guardar el archivo .txt
        ruta_archivo = os.path.join("detalles", f"{resolucion}.txt")
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            f.write(f"Título: {titulo}\n\n")
            f.write(cuerpo)

        print(f"Archivo guardado en: {ruta_archivo}")
        return {
            'Título': titulo,
            'Texto': cuerpo,
            'Archivo': ruta_archivo,
            'Enlace': url_detalle
        }

    except Exception as e:
        print(f"Error al obtener detalles del aviso: {e}")
        return None
