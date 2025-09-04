# market_analyst.py

import sys
import os
import json
from datetime import datetime
from book_generator.llm_handler import LLMHandler
from book_generator.performance_logger import PerformanceLogger
import config

def main():
    """
    Herramienta independiente para invocar al Agente Gerente Comercial
    y obtener ideas estratégicas de libros.
    """
    print("\n" + "="*80)
    print("📈 INVOCANDO AL GERENTE COMERCIAL PARA ANÁLISIS DE MERCADO 📈")
    print("="*80)

    # --- Configuración del Entorno ---
    # Se crea un manifest y logger temporales para esta consulta específica
    with open('agent_manifest.json', 'r', encoding='utf-8') as f:
        agent_manifest = {agent['agent_id']: agent for agent in json.load(f)['agents']}
    
    # Usamos un logger temporal que no se guarda en un workspace
    performance_logger = PerformanceLogger("workspace") 

    # El Gerente Comercial necesita el modelo más potente para análisis estratégico
    analyst_llm = LLMHandler(
        api_key=config.API_KEY,
        model_name=config.HEAVY_MODEL_NAME,
        performance_logger=performance_logger,
        agent_manifest=agent_manifest
    )

    # --- Llamada al Agente ---
    print("\nAnalizando tendencias y oportunidades de mercado... Por favor, espere.\n")
    
    # Necesitamos asegurarnos de que el prompt de manager_agents esté disponible
    from prompts import manager_agents
    
    report, _ = analyst_llm.call_agent(
        "commercial_manager_analyst",
        current_date=datetime.now().strftime("%Y-%m-%d")
    )

    # --- Presentación de Resultados ---
    if report and "propuestas_de_libros" in report:
        print("--- 📊 INFORME DE OPORTUNIDADES DE MERCADO 📊 ---\n")
        for i, propuesta in enumerate(report["propuestas_de_libros"], 1):
            print(f"--- PROPUESTA #{i} ---")
            print(f"📘 TEMA: {propuesta.get('tema_propuesto', 'N/A')}")
            print(f"🎯 PÚBLICO OBJETIVO: {propuesta.get('publico_objetivo', 'N/A')}")
            print(f"💡 JUSTIFICACIÓN COMERCIAL: {propuesta.get('justificacion_comercial', 'N/A')}\n")
        print("="*80)
        print("Utiliza uno de estos temas al iniciar un nuevo proyecto en 'main.py'")
        print("="*80)
    else:
        print("\n--- ❌ ERROR ---")
        print("El Gerente Comercial no pudo generar un informe. Revisa la consola en busca de errores.")

if __name__ == "__main__":
    # Aseguramos que el path del proyecto esté disponible para las importaciones
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    main()