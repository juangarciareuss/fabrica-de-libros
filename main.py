import sys
import logging
import json
import os
from book_generator.orchestrator import BookOrchestrator
from utils import clear_directory, display_usage_summary
import config

META_FILE_PATH = os.path.join("workspace", "last_run_meta.json")

def save_last_run_meta(topic, description):
    """Guarda los metadatos de la última ejecución."""
    os.makedirs("workspace", exist_ok=True)
    with open(META_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump({"topic": topic, "description": description}, f, indent=4)

def load_last_run_meta():
    """Carga los metadatos de la última ejecución si existen."""
    if os.path.exists(META_FILE_PATH):
        with open(META_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def main():
    """
    Punto de entrada con lógica de reanudación inteligente.
    """
    print("------------------------------------------------------------------")
    print("🤖 Fábrica de Libros v21.0 - Reanudación Inteligente 🤖")
    print("------------------------------------------------------------------")
    
    core_topic = None
    description = None

    clear_cache_choice = input("¿Deseas borrar el caché de la IA? (s/n): ").lower() == 's'
    if clear_cache_choice:
        clear_directory("cache")

    last_meta = load_last_run_meta()
    use_last = False

    if not clear_cache_choice and last_meta:
        print("\n--- Se encontró una ejecución anterior ---")
        print(f"  - TEMA: {last_meta['topic']}")
        print(f"  - DESC: {last_meta['description'][:70]}...")
        if input("¿Deseas reanudar con este tema y descripción? (s/n): ").lower() == 's':
            core_topic = last_meta['topic']
            description = last_meta['description']
            use_last = True
            print("----------------------------------------")

    if not use_last:
        if input("¿Deseas borrar los espacios de trabajo anteriores? (s/n): ").lower() == 's':
            clear_directory("workspace")
        core_topic = input("Introduce el TÉRMINO CLAVE del libro: ")
        description = input("Ahora, describe el objetivo y público del libro: ")
        
    if not config.API_KEY or not config.SEARCH_ENGINE_ID:
        logging.critical("CRÍTICO: API Key o Search Engine ID no configurados en .env")
        sys.exit(1)
        
    orchestrator = BookOrchestrator(core_topic, description)
    
    try:
        fast_handler, heavy_handler = orchestrator.run()
        save_last_run_meta(core_topic, description) # Guardar al final de una ejecución exitosa
        display_usage_summary(fast_handler, heavy_handler)
    except SystemExit as e:
        logging.warning(f"Proceso detenido: {e}")
    except Exception as e:
        logging.critical(f"Ha ocurrido un error inesperado: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

