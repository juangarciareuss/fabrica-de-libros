# main.py

import sys
import logging
import json
import os
import shutil

# Añade el directorio actual al path de Python para que encuentre el paquete book_generator
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

def clear_previous_project(meta_data):
    logging.info("Limpiando datos del proyecto anterior para empezar de cero...")
    topic = meta_data.get('topic')
    if topic:
        workspace_to_delete = WorkspaceManager.find_latest_workspace(topic)
        if workspace_to_delete and os.path.isdir(workspace_to_delete):
            try:
                shutil.rmtree(workspace_to_delete)
                logging.info(f"Directorio de trabajo '{workspace_to_delete}' eliminado.")
            except OSError as e:
                logging.error(f"Error al eliminar el directorio '{workspace_to_delete}': {e}")
    if os.path.exists(META_FILE_PATH):
        os.remove(META_FILE_PATH)
        logging.info("Archivo de metadatos anterior eliminado.")

def main():
    print("------------------------------------------------------------------")
    print("🤖 Fábrica de Libros v45.4 - Estructura Corregida ⚙️")
    print("------------------------------------------------------------------")

    last_meta = load_last_run_meta()
    queries_from_previous_run = None

    if last_meta:
        print("\n--- Se encontró un proyecto anterior ---")
        print(f"  - TEMA: {last_meta.get('topic')}")
        print(f"  - DESC: {last_meta.get('description', '')[:70]}...")
        
        if input("\n¿Desea continuar el proyecto anterior? (s/n): ").lower() == 's':
            core_topic = last_meta.get('topic')
            logging.info(f"Reanudando el proyecto: '{core_topic}'")
            latest_workspace = WorkspaceManager.find_latest_workspace(core_topic)
            
            if latest_workspace:
                orchestrator = BookOrchestrator(core_topic, "", "", [], workspace_path=latest_workspace)
                orchestrator.resume(workspace_path=latest_workspace)
            else:
                logging.error("No se encontró el directorio de trabajo para este proyecto. No se puede reanudar.")
            return
        else:
            if input("\n¿Reutilizar las consultas de búsqueda del proyecto anterior? (s/n): ").lower() == 's':
                latest_workspace = WorkspaceManager.find_latest_workspace(last_meta.get('topic'))
                if latest_workspace:
                    progress_file = os.path.join(latest_workspace, "progress.json")
                    if os.path.exists(progress_file):
                        with open(progress_file, 'r', encoding='utf-8') as f:
                            progress_data = json.load(f)
                            queries_from_previous_run = progress_data.get("web_queries")
                            if queries_from_previous_run:
                                logging.info(f"Consultas recuperadas: {queries_from_previous_run}")

            clear_previous_project(last_meta)
    
    logging.info("\n--- Iniciando un nuevo proyecto de libro desde cero ---")
    if input("¿Limpiar caché de la IA antes de empezar? (s/n): ").lower() == 's':
        clear_directory("cache")

    print("\n--- [PASO 1 de 3] DEFINICIÓN DEL LIBRO ---")
    core_topic = input("Introduce el TEMA CLAVE del libro (ej. 'IA en la Gastronomía Molecular'): ")
    print("\nDescribe en detalle la visión del libro:")
    q1 = input(" - ¿Cuál es el objetivo principal y qué problema resuelve?: ")
    q2 = input(" - ¿Quién es el público objetivo?: ")
    description = f"Objetivo: {q1}\nPúblico: {q2}"
    domain = input("\n¿Cuál es el DOMINIO TEMÁTICO? (ej. 'Tecnología e IA'): ")
    topics_to_avoid_str = input("¿Temas a EVITAR? (separados por comas): ")
    topics_to_avoid = [t.strip() for t in topics_to_avoid_str.split(',') if t.strip()]

    save_last_run_meta(core_topic, description, domain, topics_to_avoid)
    
    orchestrator = BookOrchestrator(core_topic, description, domain, topics_to_avoid, initial_queries=queries_from_previous_run)
    
    try:
        fast_handler, heavy_handler = orchestrator.run()
        if fast_handler and heavy_handler:
            display_usage_summary(fast_handler, heavy_handler)
    except SystemExit as e:
        logging.warning(f"Proceso detenido: {e}")
    except Exception as e:
        logging.critical(f"Ha ocurrido un error inesperado en main: {e}", exc_info=True)

if __name__ == "__main__":
    main()