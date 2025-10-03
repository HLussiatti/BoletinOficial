# Load Libraries
import requests
from bs4 import BeautifulSoup
from html import unescape
import pandas as pd


# Configuración de la URL base y fechas
base_url = "https://www.boletinoficial.gob.ar"

# # Configurar logger
# logging.basicConfig(
#     filename='boletin_errors.log',
#     level=logging.INFO,
#     format='%(asctime)s [%(levelname)s] %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )

response = search_avisos('energía','05/06/2025','05/06/2025')

def search_avisos(palabra, fecha_desde, fecha_hasta):
    """
    Realiza un POST a la URL de búsqueda de avisos en Primera del BORA y devuelve 
    el resultado de la búsqueda en la variable response.
    """
    # Configuración de la URL base y fechas
    base_url = "https://www.boletinoficial.gob.ar"

    url_busqueda = "/busquedaAvanzada/realizarBusqueda"
    payload = {
        "params": f'''{{
            "busquedaRubro":false,
            "hayMasResultadosBusqueda":true,
            "ejecutandoLlamadaAsincronicaBusqueda":false,
            "ultimaSeccion":"",
            "filtroPorRubrosSeccion":false,
            "filtroPorRubroBusqueda":false,
            "filtroPorSeccionBusqueda":false,
            "busquedaOriginal":true,
            "ordenamientoSegunda":false,
            "seccionesOriginales":[1],
            "ultimoItemExterno":null,
            "ultimoItemInterno":null,
            "texto":"{palabra}",
            "rubros":[],
            "nroNorma":"",
            "anioNorma":"",
            "denominacion":"",
            "tipoContratacion":"",
            "anioContratacion":"",
            "nroContratacion":"",
            "fechaDesde":"{fecha_desde}",
            "fechaHasta":"{fecha_hasta}",
            "todasLasPalabras":true,
            "comienzaDenominacion":true,
            "seccion":[1],
            "tipoBusqueda":"Avanzada",
            "numeroPagina":1,
            "ultimoRubro":""
        }}''',
        "array_volver": "[]"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": base_url,
        "Referer": "https://www.boletinoficial.gob.ar/busquedaAvanzada/primera",
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.post(base_url + url_busqueda, json=payload, headers=headers, timeout=10)
    
    # Código de estado (por ejemplo, 200, 404, 500)
    print("Status code:", response.status_code)
    # Texto de la respuesta (útil para ver HTML, errores, mensajes, etc.)
    print("Response text:", response.text)
    # Encabezados de la respuesta
    print("Headers:", response.headers)

    return response


def parse(data):
    
    """Extrae la información relevante del HTML devuelto por la búsqueda"""
    html = data["content"]["html"]
    html_limpio = unescape(html)
    soup = BeautifulSoup(html_limpio, 'html.parser')

    avisos = []
    for a in soup.select("a[href]"):
        aviso = a.find("div", class_="linea-aviso")
        if aviso:
            link = a["href"]
            ministerio = aviso.select_one(".item").get_text(strip=True)
            resolucion = aviso.select_one(".item-detalle small").get_text(strip=True)
            fecha_pub = aviso.select(".item-detalle small")[1].get_text(strip=True)
            detalles = aviso.find_all("p", class_="item-detalle")
            referencia_contenido = detalles[2] if len(detalles) > 2 else None
            
            referencia = ""
            contenido = ""
            if referencia_contenido:
                small = referencia_contenido.find("small")
                if small:
                    partes = list(small.stripped_strings)
                    if len(partes) >= 1:
                        referencia = partes[0]
                    if len(partes) > 1:
                        contenido = " ".join(partes[1:])

            avisos.append({
                "Fecha de Publicación": fecha_pub,
                "Referencia": referencia,
                "Resolución": resolucion,
                "Ministerio": ministerio,
                "Link": base_url + link,
                "Contenido":contenido,
                "Resumen": None,
                "Fecha de Ejecución": pd.to_datetime("today").strftime("%Y-%m-%d")
            })
    return avisos

