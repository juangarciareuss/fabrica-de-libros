import requests
from bs4 import BeautifulSoup
import time
import logging
import config
from PyPDF2 import PdfReader
from io import BytesIO

# Restauramos la configuración de logging a nivel de módulo para máxima robustez
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_text_from_url(url):
    """Extrae el texto principal de una URL, soportando HTML y PDF."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        if url.lower().endswith('.pdf'):
            pdf_file = BytesIO(response.content)
            reader = PdfReader(pdf_file)
            return "\n".join(page.extract_text() for page in reader.pages)
        else:
            soup = BeautifulSoup(response.content, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            main_content = soup.find('article') or soup.find('main') or soup.body
            if main_content:
                # Restauramos el filtro de calidad de contenido
                text_content = ' '.join(p.get_text(strip=True) for p in main_content.find_all('p'))
                return text_content if len(text_content) > 200 else None
            return None
    except Exception as e:
        logging.error(f"Error al procesar la URL {url}: {e}")
        return None

def perform_research_plan(queries, date_restrict=None):
    """
    Ejecuta un plan de investigación de forma agresiva para maximizar el número de fuentes.
    """
    logging.info(f"Ejecutando plan de investigación con {len(queries)} consultas...")
    all_results = {}
    search_url = "https://www.googleapis.com/customsearch/v1"
    
    for query in queries:
        logging.info(f"   -> Ejecutando búsqueda para: '{query}'")
        try:
            params = {
                'key': config.API_KEY,
                'cx': config.SEARCH_ENGINE_ID,
                'q': query,
                'num': 10 # Mantenemos la búsqueda agresiva
            }
            
            if date_restrict:
                params['dateRestrict'] = date_restrict
                logging.info(f"      (Restricción de tiempo activada: {date_restrict})")

            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            search_results = response.json()

            if 'items' in search_results:
                for item in search_results['items']:
                    link = item.get('link')
                    if link and link not in all_results:
                        all_results[link] = {
                            "title": item.get('title'),
                            "link": link,
                            "snippet": item.get('snippet')
                        }
            else:
                logging.warning(f"La búsqueda para '{query}' no arrojó resultados.")
            
            time.sleep(1)

        # Restauramos el manejo de excepciones específico
        except requests.exceptions.RequestException as e:
            logging.error(f"Error de red durante la búsqueda para '{query}': {e}")
        except Exception as e:
            logging.error(f"Error durante la búsqueda para '{query}': {e}")

    unique_sources = list(all_results.values())
    logging.info(f"Investigación completada. Se encontraron {len(unique_sources)} fuentes únicas.")
    return unique_sources

