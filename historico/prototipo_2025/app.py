import requests
from bs4 import BeautifulSoup
from datetime import datetime

def buscar_publicaciones_energia():
    url = "https://www.boletinoficial.gob.ar/search/avanzada"
    params = {
        "q": "energía",
        "seccion": "primera",
        "inicio": datetime.now().strftime("%d/%m/%Y"),
        "fin": datetime.now().strftime("%d/%m/%Y")
    }
    
    response = requests.get(url, params=params)
    soup = BeautifulSoup(response.text, "html.parser")

    publicaciones = []
    for item in soup.select(".resultado-busqueda"):
        titulo = item.select_one("h4").text.strip()
        resumen = item.select_one("p").text.strip()
        link = "https://www.boletinoficial.gob.ar" + item.select_one("a")["href"]
        publicaciones.append({"titulo": titulo, "resumen": resumen, "url": link})
    
    return publicaciones
