# book_generator/researcher.py

import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse
import feedparser
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_google_news_rss(query):
    """Obtiene URLs desde el feed RSS de Google Noticias, priorizando inglés."""
    urls = set()
    try:
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en&gl=US&ceid=US:en"
        logging.info(f"  -> [RSS] Consultando Google Noticias (Inglés) para: '{query}'")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            urls.add(entry.link)
    except Exception as e:
        logging.error(f"Error al procesar el feed RSS de Google Noticias: {e}")
    return list(urls)

def get_newsapi(query):
    """Obtiene URLs desde NewsAPI, priorizando inglés."""
    if not config.NEWSAPI_KEY:
        logging.warning("No se proporcionó una clave para NewsAPI. Omitiendo esta fuente.")
        return []
    
    urls = set()
    try:
        url = f"https://newsapi.org/v2/everything?q={quote_plus(query)}&apiKey={config.NEWSAPI_KEY}&language=en&sortBy=relevancy"
        logging.info(f"  -> [API] Consultando NewsAPI (Inglés) para: '{query}'")
        response = requests.get(url)
        response.raise_for_status()
        articles = response.json().get("articles", [])
        for article in articles:
            urls.add(article['url'])
    except Exception as e:
        logging.error(f"Error al consultar NewsAPI: {e}")
    return list(urls)
    
def parse_specific_feeds(queries):
    """Obtiene URLs desde una lista predefinida de feeds RSS de medios."""
    custom_feeds = {
        "Ars Technica": "http://feeds.arstechnica.com/arstechnica/index",
        "TechCrunch": "http://feeds.feedburner.com/TechCrunch/",
        "Stratechery": "https://stratechery.com/feed/",
        "MIT Technology Review": "https://www.technologyreview.com/feed/",
        "Wired_ES": "https://www.wired.es/rss",
        "Xataka": "https://www.xataka.com/feed",
        "Genbeta": "https://www.genbeta.com/feed",
        "Hipertextual": "https://hipertextual.com/feed"
    }
    urls = set()
    logging.info("  -> [RSS] Consultando feeds de medios específicos (Español e Inglés)...")
    
    for name, url in custom_feeds.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if any(q.lower() in entry.title.lower() for q in queries):
                    urls.add(entry.link)
        except Exception as e:
            logging.error(f"Error al procesar el feed RSS de '{name}': {e}")
    return list(urls)

def research(queries):
    """Orquesta la recolección de URLs desde múltiples capas de fuentes."""
    logging.info(f"Iniciando investigación multi-capa para {len(queries)} consultas...")
    all_urls = set()

    for query in queries:
        all_urls.update(get_google_news_rss(query))
        all_urls.update(get_newsapi(query))
    
    all_urls.update(parse_specific_feeds(queries))

    logging.info(f"Investigación multi-capa completada. Se encontraron {len(all_urls)} URLs únicas.")
    return list(all_urls)

def get_text_from_url(url_input):
    """Extrae el texto principal de una URL, sin un filtro de longitud agresivo."""
    url = url_input.get('url') if isinstance(url_input, dict) else url_input
    if not url or not isinstance(url, str): return None

    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            logging.warning(f"URL inválida descartada: {url}")
            return None
    except Exception:
        logging.warning(f"No se pudo parsear y validar la URL: {url}")
        return None

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        
        main_content = soup.find('article') or soup.find('main') or soup.body
        if main_content:
            # --- !! LÓGICA CORREGIDA !! ---
            # Se extrae el texto y se devuelve siempre que no esté completamente vacío.
            text_content = ' '.join(p.get_text(strip=True) for p in main_content.find_all('p'))
            return text_content if text_content.strip() else None
            # --- FIN DE LA CORRECCIÓN ---
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error de red al procesar la URL {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error inesperado al procesar la URL {url}: {e}")
        return None