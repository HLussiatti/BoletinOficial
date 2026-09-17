from transformers import pipeline
import fitz  # PyMuPDF
import logging


# Inicializar el modelo de resumen
resumidor = pipeline("summarization", model="facebook/bart-large-cnn")

def extraer_texto_pdf(ruta_pdf):
    try:
        doc = fitz.open(ruta_pdf)
        texto = ""
        for pagina in doc:
            texto += pagina.get_text()
        return texto.strip()
    except Exception as e:
        logging.error(f"Error al extraer texto del PDF: {ruta_pdf}, Error: {e}")
        return ""

def resumir_texto(texto, max_tokens=1024):
    if not texto:
        return ""
    
    # Truncamos si el texto es demasiado largo
    texto = texto[:4000]
    
    try:
        resumen = resumidor(texto, max_length=130, min_length=30, do_sample=False)[0]['summary_text']
        return resumen
    except Exception as e:
        logging.error(f"Error al resumir texto: {e}")
        return ""
