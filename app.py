import gradio as gr
import requests
from bs4 import BeautifulSoup
from transformers import pipeline

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

def buscar_resoluciones():
    url = "https://www.boletinoficial.gob.ar/secciones/buscar?c=1&q=energía"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.content, "html.parser")

    resultados = []

    for articulo in soup.find_all("article"):
        titulo = articulo.find("h2").text.strip()
        link = "https://www.boletinoficial.gob.ar" + articulo.find("a")["href"]
        texto = articulo.text.strip()

        salida = classifier(
            texto,
            candidate_labels=["energía", "educación", "seguridad", "decreto", "resolución"],
            multi_label=True,
        )

        if "energía" in salida["labels"][:2] and salida["scores"][0] > 0.6:
            resultados.append(f"{titulo}\n{link}")

    return "\n\n".join(resultados) if resultados else "No se encontraron resoluciones relevantes hoy."

gr.Interface(fn=buscar_resoluciones, inputs=[], outputs="text", title="Monitor de Resoluciones sobre Energía").launch()
