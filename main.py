# main.py

import sys
import logging
import json
import os
import shutil
import traceback

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from book_generator.orchestrator import BookOrchestrator
from book_generator.workspace_manager import WorkspaceManager
from utils import clear_directory, display_usage_summary
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
META_FILE_PATH = os.path.join("workspace", "last_run_meta.json")

def save_last_run_meta(topic, description, domain, topics_to_avoid):
    os.makedirs("workspace", exist_ok=True)
    with open(META_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump({"topic": topic, "description": description, "domain": domain, "topics_to_avoid": topics_to_avoid}, f, indent=4)

def load_last_run_meta():
    if os.path.exists(META_FILE_PATH):
        with open(META_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def main():
    print("------------------------------------------------------------------")
    print("🤖 Fábrica de Libros v46.0 - Control de Fases Avanzado ⚙️")
    print("------------------------------------------------------------------")

    last_meta = load_last_run_meta()
    
    if last_meta:
        print("\n--- Se encontró un proyecto anterior ---")
        print(f"  - TEMA: {last_meta.get('topic')}")
        print(f"  - DESC: {last_meta.get('description', '')[:70]}...")
        
        latest_workspace = WorkspaceManager.find_latest_workspace(last_meta.get('topic'))
        
        print("\n¿Qué deseas hacer?")
        print("  1. Reanudar el proceso donde se quedó.")
        print("  2. Ejecutar una fase específica (Control Avanzado).")
        print("  3. Empezar un proyecto completamente nuevo (borrar todo).")
        
        choice = input("Elige una opción (1, 2, 3): ")

        if choice == '1':
            if latest_workspace:
                orchestrator = BookOrchestrator(last_meta.get('topic'), "", "", [], workspace_path=latest_workspace)
                fast_handler, heavy_handler = orchestrator.resume_from_last_state()
                if fast_handler and heavy_handler:
                    display_usage_summary(fast_handler, heavy_handler)
            else:
                logging.error("No se encontró el directorio de trabajo. No se puede reanudar.")
            return

        elif choice == '2':
            print("\n  Elige la fase desde la que quieres empezar:")
            print("    a. Re-lanzar la INVESTIGACIÓN (borra investigación y capítulos).")
            print("    b. Re-lanzar la ESCRITURA (usa la investigación existente).")
            print("    c. Re-lanzar el REFINAMIENTO (usa los capítulos existentes).")
            phase_choice = input("    Elige una opción (a, b, c): ").lower()

            if phase_choice in ['a', 'b', 'c'] and latest_workspace:
                orchestrator = BookOrchestrator(last_meta.get('topic'), "", "", [], workspace_path=latest_workspace)
                fast_handler, heavy_handler = orchestrator.run_from_phase(phase_choice)
                if fast_handler and heavy_handler:
                    display_usage_summary(fast_handler, heavy_handler)
            else:
                 logging.error("Opción o workspace no válidos. No se puede continuar.")
            return
            
        elif choice == '3':
            logging.info("Borrando el proyecto anterior para empezar de cero.")
            shutil.rmtree(latest_workspace)
            os.remove(META_FILE_PATH)
        
        else:
            logging.warning("Opción no válida. Saliendo.")
            return

    # Si se llega aquí, es porque se necesita un proyecto desde cero.
    logging.info("\n--- Iniciando un nuevo proyecto de libro desde cero ---")
    if input("¿Limpiar caché de la IA antes de empezar? (s/n): ").lower() == 's':
        clear_directory("cache")

    print("\n--- [PASO 1 de 3] DEFINICIÓN DEL LIBRO ---")
    core_topic = input("Introduce el TEMA CLAVE del libro: ")
    q1 = input(" - ¿Cuál es el objetivo principal y qué problema resuelve?: ")
    q2 = input(" - ¿Quién es el público objetivo?: ")
    description = f"Objetivo: {q1}\nPúblico: {q2}"
    domain = input("\n¿Cuál es el DOMINIO TEMÁTICO?: ")
    topics_to_avoid_str = input("¿Temas a EVITAR? (separados por comas): ")
    topics_to_avoid = [t.strip() for t in topics_to_avoid_str.split(',') if t.strip()]

    save_last_run_meta(core_topic, description, domain, topics_to_avoid)
    orchestrator = BookOrchestrator(core_topic, description, domain, topics_to_avoid)
    fast_handler, heavy_handler = orchestrator.run_full_process()
    if fast_handler and heavy_handler:
        display_usage_summary(fast_handler, heavy_handler)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n" + "="*80)
        print("    OCURRIÓ UN ERROR CRÍTICO QUE IMPIDIÓ LA EJECUCIÓN")
        print("="*80)
        logging.critical(f"Error no capturado en main: {e}", exc_info=True)
        traceback.print_exc() 
        print("="*80)
        input("\nPresiona Enter para salir...")