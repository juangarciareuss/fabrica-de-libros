# cover_designer.py

import sys
import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
import google.generativeai as genai
from book_generator.llm_handler import LLMHandler
from book_generator.performance_logger import PerformanceLogger
from book_generator.workspace_manager import WorkspaceManager
import config
from prompts import designer_agents

# Cargar variables de entorno desde .env
load_dotenv()

def main():
    """
    Herramienta que intenta generar una portada con DALL-E 3 y, si falla,
    guarda un prompt optimizado para ser usado manualmente en Gemini.
    """
    print("\n" + "="*80)
    print("🎨 INVOCANDO AL SISTEMA DE DISEÑO DE PORTADAS (CON RESPALDO) 🎨")
    print("="*80)

    # --- Cargar Información del Último Proyecto ---
    meta_path = os.path.join("workspace", "last_run_meta.json")
    if not os.path.exists(meta_path):
        print("ERROR: No se encontró 'last_run_meta.json'. Ejecuta 'main.py' primero.")
        return

    with open(meta_path, 'r', encoding='utf-8') as f:
        last_meta = json.load(f)
    
    book_topic = last_meta.get("topic")
    book_description = last_meta.get("description")

    workspace_path = WorkspaceManager.find_latest_workspace(book_topic)
    if not workspace_path:
        print(f"ERROR: No se encontró un workspace para el tema '{book_topic}'.")
        return

    print(f"\nDiseñando portada para el libro: '{book_topic}'...\n")

    # --- Configuración de Agentes ---
    with open('agent_manifest.json', 'r', encoding='utf-8') as f:
        agent_manifest = {agent['agent_id']: agent for agent in json.load(f)['agents']}
    
    performance_logger = PerformanceLogger(workspace_path) 
    
    designer_llm = LLMHandler(
        api_key=config.API_KEY,
        model_name=config.HEAVY_MODEL_NAME,
        performance_logger=performance_logger,
        agent_manifest=agent_manifest
    )

    # --- Fase 1: Intentar con DALL-E 3 (Plan A) ---
    print("--- PLAN A: Intentando generar con DALL-E 3 ---")
    try:
        print("1. El Director de Arte está conceptualizando el prompt...")
        raw_response, _ = designer_llm.call_agent("cover_designer", book_topic=book_topic, book_description=book_description)
        final_dalle_prompt = str(raw_response.get('prompt', raw_response)) if isinstance(raw_response, dict) else str(raw_response)

        print(f"   -> Prompt para DALL-E (extraído): \"{final_dalle_prompt}\"\n")
        print("2. Conectando con DALL-E 3...")
        
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("La clave de API de OpenAI no se encontró en .env")

        client = OpenAI(api_key=openai_api_key)
        response = client.images.generate(model="dall-e-3", prompt=final_dalle_prompt, size="1024x1792", quality="hd", n=1)
        image_url = response.data[0].url
        print("   -> ✅ Portada generada exitosamente con DALL-E.\n")

        print("3. Descargando y guardando la portada...")
        image_data = requests.get(image_url).content
        cover_path = os.path.join(workspace_path, "portada_generada_dalle.png")
        with open(cover_path, 'wb') as handler:
            handler.write(image_data)
        
        print_success_message(cover_path)

    except Exception as e:
        print("\n--- ❌ ERROR EN PLAN A (DALL-E) ---")
        print(f"Detalle: {e}")
        print("Iniciando sistema de respaldo...\n")

        # --- Fase 2: Generar un Prompt para Google Gemini (Plan B) ---
        print("--- PLAN B: Generando un prompt de alta calidad para Gemini ---")
        try:
            print("1. Activando el diseñador interno para crear un prompt para Gemini...")
            
            gemini_prompt, _ = designer_llm.call_agent(
                "cover_designer_gemini",
                book_topic=book_topic,
                book_description=book_description
            )
            
            if not gemini_prompt:
                 raise ValueError("El Director de Arte no pudo generar un prompt para Gemini.")

            # --- !! LÓGICA DE GUARDADO DEL PROMPT !! ---
            cover_path = os.path.join(workspace_path, "portada_prompt_gemini.txt")
            with open(cover_path, 'w', encoding='utf-8') as f:
                f.write(gemini_prompt)
            
            print_success_message(cover_path, is_prompt=True)
            # --- FIN DE LA LÓGICA DE GUARDADO ---

        except Exception as gemini_e:
            print("\n--- ❌ ERROR EN PLAN B (Gemini) ---")
            print(f"El sistema de respaldo también falló. Detalle: {gemini_e}")

def print_success_message(path, is_prompt=False):
    print("\n" + "="*80)
    if is_prompt:
        print(f"✅ ¡ÉXITO DEL PLAN DE RESPALDO! Se ha guardado un prompt de alta calidad en:")
        print(f"   -> {path}")
        print("\nCOPIA el contenido de ese archivo y pégalo en Google AI Studio o en la app de Gemini para generar tu portada.")
    else:
        print(f"🎉 ¡ÉXITO! La portada ha sido guardada en:")
        print(f"   -> {path}")
    print("="*80)

if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    main()