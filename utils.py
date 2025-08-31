import logging
import shutil
import os
import config

def clear_directory(path):
    """Limpia un directorio si existe."""
    if os.path.exists(path):
        shutil.rmtree(path)
        logging.info(f"🧹 Directorio '{path}' borrado.")

def display_usage_summary(fast_handler, heavy_handler):
    """Muestra un resumen del uso de tokens y el costo estimado."""
    fast_usage = fast_handler.get_token_usage()
    heavy_usage = heavy_handler.get_token_usage()
    
    fast_cost = (fast_usage['total'] / 1_000_000) * (config.TOKEN_PRICES[config.FAST_MODEL_NAME]['input'] + config.TOKEN_PRICES[config.FAST_MODEL_NAME]['output']) / 2
    heavy_cost = (heavy_usage['total'] / 1_000_000) * (config.TOKEN_PRICES[config.HEAVY_MODEL_NAME]['input'] + config.TOKEN_PRICES[config.HEAVY_MODEL_NAME]['output']) / 2

    total_tokens = fast_usage['total'] + heavy_usage['total']
    total_cost = fast_cost + heavy_cost

    print("\n--- 📊 INFORME DE CONSUMO DE TOKENS Y COSTOS 📊 ---")
    print(f"Modelo Rápido ({config.FAST_MODEL_NAME}):")
    print(f"  - Tokens Totales: {fast_usage['total']:,}")
    print(f"  - Costo Estimado: ${fast_cost:.4f} USD")
    print("-" * 50)
    print(f"Modelo Pesado ({config.HEAVY_MODEL_NAME}):")
    print(f"  - Tokens Totales: {heavy_usage['total']:,}")
    print(f"  - Costo Estimado: ${heavy_cost:.4f} USD")
    print("=" * 50)
    print(f"TOTALES DE LA EJECUCIÓN:")
    print(f"  - Tokens Combinados: {total_tokens:,}")
    print(f"  - Costo Total Estimado: ${total_cost:.4f} USD")
    print("--------------------------------------------------")

