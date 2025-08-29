import requests
from bs4 import BeautifulSoup
import time
import logging
import config
from PyPDF2 import PdfReader
from io import BytesIO

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_text_from_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        if url.lower().endswith('.pdf'):
            logging.info(f"Detectado archivo PDF en {url}. Extrayendo texto...")
            pdf_file = BytesIO(response.content)
            reader = PdfReader(pdf_file)
            text_content = ""
            for page in reader.pages:
                text_content += page.extract_text() + "\n"
            return text_content
        else:
            soup = BeautifulSoup(response.content, 'html.parser')
            main_content_tags = soup.find('article') or soup.find('main') or soup.find('div', role='main')
            if main_content_tags:
                paragraphs = main_content_tags.find_all('p')
            else:
                paragraphs = soup.find_all('p')
            text_content = ' '.join([p.get_text(strip=True) for p in paragraphs])
            if len(text_content) < 300: # Umbral más bajo para noticias cortas
                logging.warning(f"El contenido extraído de {url} es muy corto.")
                return None
            return text_content
    except Exception as e:
        logging.error(f"Ocurrió un error al procesar {url}: {e}")
        return None

def perform_research(topic, num_results=10):
    """
    Realiza una búsqueda web usando TU motor de búsqueda personalizado de Google.
    """
    logging.info(f"Iniciando investigación para: '{topic}' usando tu motor de búsqueda personalizado.")
    try:
        search_url = "https://www.googleapis.com/customsearch/v1"
        
        # --- LÍNEA CORREGIDA ---
        # Volvemos a añadir el 'cx', que es el ID de tu motor de búsqueda.
        # Esto le dice a Google que busque dentro de tu universo de 100+ sitios.
        params = {
            'key': config.API_KEY,
            'cx': config.SEARCH_ENGINE_ID, # <-- ESTA LÍNEA ES LA CLAVE
            'q': topic,
            'num': num_results
        }
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        search_results = response.json()

        if 'items' not in search_results or len(search_results['items']) == 0:
            logging.error("Tu motor de búsqueda no devolvió ningún resultado para este tema.")
            return []
        
        candidate_sources = [
            {"title": item.get('title'), "link": item.get('link'), "snippet": item.get('snippet')}
            for item in search_results['items']
        ]
        return candidate_sources

    except Exception as e:
        logging.critical(f"Un error crítico ocurrió durante la investigación: {e}")
        return []