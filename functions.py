# Load Libraries
import requests
from bs4 import BeautifulSoup
from html import unescape
from datetime import date
import pandas as pd
import logging
import base64
import re
import os


def nuevos_avisos(avisos_totales,database):
    """
    Devuelve un DataFrame con los avisos que están en avisos_totales pero no en database.
    Compara usando las columnas 'Resolución' y 'Referencia'.
    Soporta entrada como lista de dicts o DataFrame.
    """
    # Transforma avisos_totales a DataFrame si es necesario
    if isinstance(avisos_totales, list):
        avisos_totales = pd.DataFrame(avisos_totales)

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

