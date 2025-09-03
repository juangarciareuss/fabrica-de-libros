# audit.py
import os
import json
from book_generator.llm_handler import LLMHandler
from book_generator.workspace_manager import WorkspaceManager
from prompts import audit_agents # Necesitarás ajustar la importación

def create_audit_dossier(workspace_path):
    """Recopila todos los datos de una ejecución en un único string."""
    dossier_parts = []
    
    # 1. Cargar el progress.json
    progress_file = os.path.join(workspace_path, 'progress.json')
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
        dossier_parts.append("--- PROGRESS.JSON ---\n" + json.dumps(progress_data, indent=2, ensure_ascii=False))

    # 2. Cargar los prompts (esto es simplificado, podrías leer los archivos .py directamente)
    from prompts import quality_agents, research_agents # etc.
    dossier_parts.append("\n\n--- PROMPTS UTILIZADOS ---\n")
    dossier_parts.append("CRITIQUE_PROMPT:\n" + quality_agents.CRITIQUE_PROMPT)
    dossier_parts.append("\nREFACTOR_CHAPTER_PROMPT:\n" + quality_agents.REFACTOR_CHAPTER_PROMPT)
    # ... añadir más prompts ...

    # 3. Cargar el log (simplificado, idealmente buscarías el log específico de esa ejecución)
    # Por ahora, podrías leer las últimas N líneas de un log general.
    # ... Lógica para leer el log y extraer warnings/errors ...
    
    return "\n\n".join(dossier_parts)

def main():
    print("--- 🔬 Iniciando Auditoría de Sistema ---")
    
    # Pedir al usuario el tema del libro a auditar
    book_topic = input("Introduce el TEMA CLAVE del libro que quieres auditar: ")
    workspace_path = WorkspaceManager.find_latest_workspace(book_topic)

    if not workspace_path:
        print(f"No se encontró un workspace para el tema '{book_topic}'.")
        return

    print(f"Generando dossier para el workspace: {workspace_path}")
    dossier_content = create_audit_dossier(workspace_path)

    # Inicializar un LLMHandler (puede ser el rápido para esto)
    auditor_llm = LLMHandler(api_key="TU_API_KEY", model_name="gemini-1.5-flash-latest")
    
    # Llamar al agente auditor
    print("El Agente Auditor está analizando el dossier...")
    audit_report = auditor_llm.run_system_audit(dossier_content) # Necesitarás crear este método en LLMHandler

    print("\n\n--- INFORME DE AUDITORÍA ---")
    print(audit_report)

if __name__ == "__main__":
    main()