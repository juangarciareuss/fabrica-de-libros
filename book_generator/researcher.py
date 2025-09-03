import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import feedparser
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CAPA 1: RSS DE GOOGLE NOTICIAS ---
def get_google_news_rss(query):
    """Obtiene URLs desde el feed RSS de Google Noticias."""
    urls = set()
    try:
        # Formato de la URL del feed RSS de Google Noticias
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=es-419&gl=US&ceid=US:es-419"
        logging.info(f"  -> [RSS] Consultando Google Noticias para: '{query}'")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            urls.add(entry.link)
    except Exception as e:
        logging.error(f"Error al procesar el feed RSS de Google Noticias: {e}")
    return list(urls)

# --- CAPA 2: NEWSAPI (REQUIERE CLAVE) ---
def get_newsapi(query):
    """Obtiene URLs desde NewsAPI. Requiere una API Key."""
    if not config.NEWSAPI_KEY:
        logging.warning("No se proporcionó una clave para NewsAPI. Omitiendo esta fuente.")
        return []
    
    urls = set()
    try:
        # Documentación: https://newsapi.org/docs/endpoints/everything
        url = f"https://newsapi.org/v2/everything?q={quote_plus(query)}&apiKey={config.NEWSAPI_KEY}&language=es&sortBy=relevancy"
        logging.info(f"  -> [API] Consultando NewsAPI para: '{query}'")
        response = requests.get(url)
        response.raise_for_status()
        articles = response.json().get("articles", [])
        for article in articles:
            urls.add(article['url'])
    except Exception as e:
        logging.error(f"Error al consultar NewsAPI: {e}")
    return list(urls)
    
# --- CAPA 3: RSS DE MEDIOS ESPECÍFICOS ---
def parse_specific_feeds(queries):
    """Obtiene URLs desde una lista predefinida de feeds RSS de medios de tecnología."""
    custom_feeds = {
        "Wired_ES": "https://www.wired.es/rss",
        "Xataka": "https://www.xataka.com/feed",
        "Genbeta": "https://www.genbeta.com/feed",
        "Hipertextual": "https://hipertextual.com/feed"
    }
    urls = set()
    logging.info("  -> [RSS] Consultando feeds de medios específicos...")
    
    for name, url in custom_feeds.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                # Comprueba si alguna de las palabras clave de la consulta está en el título
                if any(q.lower() in entry.title.lower() for q in queries):
                    urls.add(entry.link)
        except Exception as e:
            logging.error(f"Error al procesar el feed RSS de '{name}': {e}")
    return list(urls)

# --- FUNCIÓN PRINCIPAL DE INVESTIGACIÓN ---
def research(queries):
    """
    Orquesta la recolección de URLs desde múltiples capas de fuentes.
    """
    logging.info(f"Iniciando investigación multi-capa para {len(queries)} consultas...")
    all_urls = set()

    for query in queries:
        # Capa 1: Google News RSS
        all_urls.update(get_google_news_rss(query))
        
        # Capa 2: NewsAPI
        all_urls.update(get_newsapi(query))
    
    # Capa 3: Feeds Específicos (se ejecuta una vez con todas las queries como keywords)
    all_urls.update(parse_specific_feeds(queries))

    logging.info(f"Investigación multi-capa completada. Se encontraron {len(all_urls)} URLs únicas.")
    return list(all_urls)

# --- FUNCIÓN PARA EXTRAER CONTENIDO (SIN CAMBIOS) ---
def get_text_from_url(url_input):
    """Extrae el texto principal de una URL, aceptando un string o un dict."""
    # --- VVVV LÓGICA DE ROBUSTEZ AÑADIDA VVVV ---
    if isinstance(url_input, dict):
        url = url_input.get('url')
    else:
        url = url_input

    if not url or not isinstance(url, str):
        logging.error(f"Se recibió una entrada no válida para la extracción de URL: {url_input}")
        return None
    # --- ^^^^ FIN DE LA LÓGICA AÑADIDA ^^^^ ---

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        
        main_content = soup.find('article') or soup.find('main') or soup.body
        if main_content:
            text_content = ' '.join(p.get_text(strip=True) for p in main_content.find_all('p'))
            return text_content if len(text_content) > 200 else None
        return None
    except Exception as e:
        logging.error(f"Error al procesar la URL {url}: {e}")
        return None