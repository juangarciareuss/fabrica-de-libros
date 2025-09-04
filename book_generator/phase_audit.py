# book_generator/phase_audit.py

import logging
import json
import config
from .llm_handler import LLMHandler

class PhaseAudit:
    """
    Gestiona la fase de auditoría de contenido, identificando lagunas de información
    y enriqueciendo automáticamente el borrador.
    """
    def __init__(self, state, workspace, performance_logger, agent_manifest):
        self.state = state
        self.workspace = workspace
        self.performance_logger = performance_logger
        self.agent_manifest = agent_manifest
        
        handler_args = {
            "performance_logger": self.performance_logger,
            "agent_manifest": self.agent_manifest
        }
        self.llm_fast = LLMHandler(config.API_KEY, config.FAST_MODEL_NAME, **handler_args)
        self.llm_heavy = LLMHandler(config.API_KEY, config.HEAVY_MODEL_NAME, **handler_args)

    def execute(self):
        logging.info("\n--- [FASE 3 - AUDITORÍA] ANÁLISIS DE COBERTURA DE CONTENIDO ---")
        
        research_dossier = self.workspace.load_structured_research()
        youtube_transcript = self.workspace.read_youtube_transcript("Youtube.txt")
        
        full_research_text = json.dumps(research_dossier, indent=2, ensure_ascii=False)
        if youtube_transcript:
            full_research_text += "\n\n--- TRANSCRIPCIÓN DE YOUTUBE ---\n" + youtube_transcript

        book_manuscript_content = "\n\n---\n\n".join(
            [f"# {chap['title']}\n{chap['content']}" for chap in self.state.get("book_content", []) if chap.get('content')]
        )

        if not book_manuscript_content:
            logging.warning("No hay contenido en el libro para auditar. Saltando fase.")
            return True

        logging.info("  -> Activando Agente Auditor para encontrar contenido valioso no utilizado...")
        
        # --- !! LÍNEA CORREGIDA !! ---
        # Se usa la clave 'book_manuscrito' que el prompt espera.
        audit_report, _ = self.llm_heavy.call_agent(
            "content_auditor",
            research_dossier=full_research_text,
            book_manuscrito=book_manuscript_content
        )
        # --- FIN DE LA CORRECCIÓN ---

        if not audit_report or not audit_report.get("refactoring_plan"):
            logging.info("El Auditor no encontró mejoras significativas o falló. Pasando a la siguiente fase.")
            return True

        logging.info("✅ Auditoría completada. Se encontraron mejoras de contenido.")
        self.workspace.save_json("audit_report.json", audit_report)

        logging.info("\n--- [FASE 3.1 - MEJORA AUTOMÁTICA] APLICANDO SUGERENCIAS DEL AUDITOR ---")
        for plan in audit_report.get("refactoring_plan", []):
            target_title = plan.get("chapter_title")
            instructions = "\n- ".join(plan.get("instructions", []))
            
            if not target_title or not instructions:
                continue

            target_chapter_index = -1
            for i, chap in enumerate(self.state["book_content"]):
                if chap.get("title") == target_title:
                    target_chapter_index = i
                    break
            
            if target_chapter_index != -1:
                logging.info(f"  -> Mejorando capítulo: '{target_title}'")
                original_chapter = self.state["book_content"][target_chapter_index]
                
                new_content_data, _ = self.llm_heavy.call_agent(
                    "refactor_generic_fallback",
                    chapter_title=original_chapter["title"],
                    original_content=original_chapter["content"],
                    critique_feedback="[]", 
                    user_feedback=f"Un auditor ha revisado el libro y ha solicitado las siguientes mejoras para este capítulo:\n- {instructions}",
                    topics_to_avoid=self.state.get("topics_to_avoid", [])
                )

                if new_content_data and new_content_data.get('rewritten_chapter'):
                    self.state["book_content"][target_chapter_index]['content'] = new_content_data['rewritten_chapter']
                    logging.info(f"  -> Éxito al enriquecer '{target_title}'.")
                    self.workspace.save_chapter(target_chapter_index + 1, original_chapter['title'], new_content_data['rewritten_chapter'])
                    self.workspace.save_progress(self.state)
                else:
                    logging.error(f"  -> El refactorizador no pudo aplicar las mejoras del auditor al capítulo '{target_title}'.")
            else:
                logging.warning(f"  -> El auditor sugirió mejoras para un capítulo no encontrado: '{target_title}'")
        return True