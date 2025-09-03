# book_generator/phase_research.py

import logging
import json
import config
from .llm_handler import LLMHandler
from .researcher import research, get_text_from_url

class PhaseResearch:
    """
    Gestiona la fase de investigación del libro, desde la generación de consultas
    hasta la curación y estructuración del contenido final.
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
        """
        Orquesta el flujo completo de la fase de investigación.
        """
        logging.info("\n--- [FASE 1] INVESTIGACIÓN Y DESTILACIÓN DE INTELIGENCIA ---")
        
        if not self.state.get("web_queries"):
            logging.info("  -> Paso 1.1: Generando consultas de búsqueda iniciales...")
            queries_data, _ = self.llm_fast.generate_web_queries(
                topic=self.state["core_topic"],
                description=self.state["description"]
            )
            if not queries_data or "queries" not in queries_data:
                logging.error("Fallo crítico: El agente no pudo generar las consultas de búsqueda.")
                return False
            self.state["web_queries"] = queries_data["queries"]
            self.workspace.save_progress(self.state)
        
        logging.info(f"  -> Paso 1.2: Realizando búsqueda multi-capa con las consultas: {self.state['web_queries']}")
        all_urls = research(self.state["web_queries"])
        if not all_urls:
            logging.warning("La investigación web no arrojó URLs. Se procederá solo con fuentes locales si existen.")
        
        full_content_for_analysis = ""
        curated_sources_list = []
        source_id_counter = 1

        # MEJORA: Se procesan TODAS las URLs, sin pre-selección.
        if all_urls:
            logging.info(f"  -> Paso 1.3: Extrayendo contenido completo de {len(all_urls)} URLs encontradas...")
            for url in all_urls:
                text = get_text_from_url(url)
                if text:
                    full_content_for_analysis += f"--- URL FUENTE: {url} ---\n{text}\n\n"
                    curated_sources_list.append({"id": source_id_counter, "url": url, "snippet": text[:200] + "..."})
                    source_id_counter += 1

        youtube_transcript = self.workspace.read_youtube_transcript("Youtube.txt")
        if youtube_transcript:
            logging.info("  -> Paso 1.4: Incorporando transcripción de YouTube a la investigación.")
            full_content_for_analysis += f"--- FUENTE: YouTube Transcript ---\n{youtube_transcript}\n\n"
            self.state['youtube_transcript_available'] = True
        
        if not full_content_for_analysis:
            logging.critical("Fallo total de la investigación: No se pudo recopilar contenido. Abortando.")
            return False

        self.state['curated_sources'] = curated_sources_list
        self.workspace.save_bibliography(curated_sources_list)

        logging.info("  -> Paso 1.5: Activando Destilador de Inteligencia para analizar y estructurar toda la investigación...")
        structured_research, _ = self.llm_heavy.curate_and_structure_research(
            topic=self.state["core_topic"],
            full_content_for_analysis=full_content_for_analysis
        )
        if not structured_research:
            logging.error("Fallo crítico: El Destilador de Inteligencia no pudo estructurar la investigación.")
            return False

        self.state["research_catalog"] = structured_research
        self.workspace.save_structured_research(structured_research)
        self.workspace.save_progress(self.state)

        logging.info("✅ Fase de investigación y destilación completada exitosamente.")
        return True