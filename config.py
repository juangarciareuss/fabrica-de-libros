import os
from dotenv import load_dotenv

load_dotenv()

# --- CLAVES DE API Y CONFIGURACIÓN ---
API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY") # <-- CLAVE AÑADIDA PARA NEWSAPI

# --- ARQUITECTURA MULTI-MODELO OPTIMIZADA ---
FAST_MODEL_NAME = "gemini-1.5-flash-latest"
HEAVY_MODEL_NAME = "gemini-1.5-pro-latest"

# --- UMBRALES DE CALIDAD Y CICLOS DE REFINAMIENTO ---
MIN_SCORE_FOR_APPROVAL = 9.0
MAX_REFINEMENT_CYCLES = 3

# --- UMBRAL DE RIGOR ACADÉMICO ---
MIN_SOURCES_FOR_BOOK = 20

# --- PRECIOS DE TOKENS PARA CÁLCULO DE COSTOS (USD por 1M de tokens) ---
TOKEN_PRICES = {
    "gemini-1.5-flash-latest": {"input": 0.35, "output": 0.70},
    "gemini-1.5-pro-latest": {"input": 3.50, "output": 7.00},
}