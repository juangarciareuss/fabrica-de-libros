# book_generator/phase_research.py

import logging
import json
import config
from .llm_handler import LLMHandler
from .researcher import research, get_text_from_url

class PhaseResearch:
    """
    Gestiona la fase de investigación del libro de forma robusta,
    utilizando el despachador de agentes optimizado.
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
        logging.info("\n--- [FASE 1] INVESTIGACIÓN Y DESTILACIÓN DE INTELIGENCIA ---")
        
        if not self.state.get("web_queries"):
            logging.info("  -> Paso 1.1: Generando consultas de búsqueda iniciales...")
            queries_data, _ = self.llm_fast.call_agent(
                "research_web_query_generator",
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
        
        web_content = ""
        curated_sources_list = []
        source_id_counter = 1

        if all_urls:
            logging.info(f"  -> Paso 1.3: Extrayendo contenido de {len(all_urls)} URLs...")
            for url in all_urls:
                text = get_text_from_url(url)
                if text:
                    web_content += f"--- URL FUENTE: {url} ---\n{text}\n\n"
                    curated_sources_list.append({"id": source_id_counter, "url": url, "snippet": text[:200] + "..."})
                    source_id_counter += 1
        
        # Leemos el contenido de YouTube. Si está vacío, la variable será un string vacío.
        youtube_transcript = self.workspace.read_youtube_transcript("Youtube.txt")
        
        # --- LÓGICA DE COMBINACIÓN Y VALIDACIÓN ROBUSTA ---
        full_content_for_analysis = web_content
        if youtube_transcript:
            logging.info("  -> Paso 1.4: Incorporando transcripción de YouTube a la investigación.")
            full_content_for_analysis += f"--- FUENTE: YouTube Transcript ---\n{youtube_transcript}\n\n"
        else:
            logging.info("  -> Paso 1.4: No se encontró contenido en 'Youtube.txt' o el archivo está vacío. Se omitirá.")

        if not full_content_for_analysis.strip():
            logging.critical("Fallo total de la investigación: No se pudo recopilar contenido de NINGUNA fuente (ni web ni YouTube). Abortando.")
            return False
        elif not web_content.strip() and youtube_transcript:
            logging.warning("La investigación web no arrojó contenido. El libro se basará únicamente en la transcripción de YouTube.")
        elif web_content.strip() and not youtube_transcript:
            logging.info("No se utilizó contenido de YouTube. El libro se basará únicamente en la investigación web.")
        
        self.state['curated_sources'] = curated_sources_list
        self.workspace.save_bibliography(curated_sources_list)

        logging.info("  -> Paso 1.5: Activando Destilador de Inteligencia...")
        structured_research, _ = self.llm_heavy.call_agent(
            "research_master_curator",
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