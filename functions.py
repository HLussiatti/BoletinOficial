# Load Libraries
import requests
from bs4 import BeautifulSoup
from html import unescape
from datetime import date
import pandas as pd
import logging


# Configuración de la URL base y fechas
base_url = "https://www.boletinoficial.gob.ar"
fecha_desde = date.today().strftime("%d/%m/%Y")
fecha_hasta = date.today().strftime("%d/%m/%Y")

# # Configurar logger
# logging.basicConfig(
#     filename='boletin_errors.log',
#     level=logging.INFO,
#     format='%(asctime)s [%(levelname)s] %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )


def post(text):    
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
            "texto":"{text}",
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
        "Referer": "https://www.boletinoficial.gob.ar/busquedaAvanzada/all",
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.post(base_url + url_busqueda, data=payload, headers=headers)
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
                "Resolución": resolucion,
                "Ministerio": ministerio,
                "Link": base_url + link,
                "Fecha de Publicación": fecha_pub,
                "Referencia": referencia,
                "Contenido":contenido,
                "Resumen": None 
            })
    return avisos


def nuevos_avisos(avisos_totales,database):
    """
    Devuelve un DataFrame con los avisos que están en avisos_totales pero no en database.
    Compara usando las columnas 'Resolución' y 'Referencia'.
    Soporta entrada como lista de dicts o DataFrame.
    """
    # Asegurar que ambos son DataFrames
    if isinstance(avisos_totales, list):
        avisos_totales = pd.DataFrame(avisos_totales)
    if isinstance(database, list):
        database = pd.DataFrame(database)

    # Validar columnas necesarias
    if not {'Resolución', 'Referencia'}.issubset(avisos_totales.columns) or \
       not {'Resolución', 'Referencia'}.issubset(database.columns):
        raise ValueError("Ambos DataFrames deben contener las columnas 'Resolución' y 'Referencia'.")

    # Identificar avisos nuevos
    df_merged = avisos_totales.merge(
        database[['Resolución', 'Referencia']],
        on=['Resolución', 'Referencia'],
        how='left',
        indicator=True
    )
    df_nuevos = df_merged[df_merged['_merge'] == 'left_only'].drop(columns=['_merge'])

    return df_nuevos.reset_index(drop=True)


def guardar_avisos(nuevos_avisos,database):
    """Guarda los avisos en la base de datos, eliminando duplicados y formateando fechas."""

    # Convertir a DataFrame y formatear Fecha de Publicación
    df_avisos = pd.DataFrame(nuevos_avisos)
    df_avisos["Fecha de Publicación"] = df_avisos["Fecha de Publicación"].str.replace("Fecha de Publicacion: ", "")
    df_avisos["Fecha de Publicación"] = pd.to_datetime(df_avisos["Fecha de Publicación"], format="%d/%m/%Y", errors="coerce")
    
    # Agregar columna de fecha de ejecución
    df_avisos["Fecha de Ejecución"] = date.today()
    
    # Concatenar y eliminar duplicados basados en columnas clave
    base = pd.concat([database, df_avisos], ignore_index=True)
    base.drop_duplicates(subset=["Resolución", "Referencia"], inplace=True)
    
    # Formatear y ordenar
    base["Fecha de Publicación"] = pd.to_datetime(base["Fecha de Publicación"], errors='coerce', dayfirst=True)
    base = base.sort_values("Fecha de Publicación", ascending=False)
    
    # Guardar en el archivo Excel
    base.to_excel("database.xlsx", index=False)

    logging.info(f"{len(df_avisos)} avisos procesados y guardados.")
    return df_avisos
