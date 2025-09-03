# book_generator/orchestrator.py
import logging
import sys
import json
from .workspace_manager import WorkspaceManager
from .phase_research import PhaseResearch
from .phase_writing import PhaseWriting
from .phase_refinement import PhaseRefinement
from .performance_logger import PerformanceLogger

class BookOrchestrator:
    def __init__(self, core_topic, description, domain, topics_to_avoid, workspace_path=None):
        self.state = {
            "core_topic": core_topic, "description": description, "domain": domain,
            "topics_to_avoid": topics_to_avoid, "book_content": [], "research_catalog": None,
            "youtube_transcript": None, "curated_sources": None, "table_of_contents": None,
        }
        
        self.workspace = WorkspaceManager(core_topic, existing_path=workspace_path)
        
        # <<< MEJORA: Se carga el manifest y se crea el logger >>>
        with open('agent_manifest.json', 'r', encoding='utf-8') as f:
            self.agent_manifest = {agent['agent_id']: agent for agent in json.load(f)['agents']}
        
        self.performance_logger = PerformanceLogger(self.workspace.workspace_dir)

        # Pasamos el logger y el manifest a cada fase
        common_args = {
            "state": self.state,
            "workspace": self.workspace,
            "performance_logger": self.performance_logger,
            "agent_manifest": self.agent_manifest
        }
        self.researcher = PhaseResearch(**common_args)
        self.writer = PhaseWriting(**common_args)
        self.refiner = PhaseRefinement(**common_args)

        logging.info(f"Orquestador inicializado. Workspace en: '{self.workspace.workspace_dir}'")

    def run(self):
        try:
            if not self.researcher.execute():
                logging.critical("La fase de investigación falló. Abortando.")
                return None, None
            if not self.writer.execute():
                logging.critical("La fase de escritura falló. Abortando.")
                return None, None
            if not self.refiner.execute():
                logging.critical("La fase de refinamiento falló. Abortando.")
                return None, None
            
            final_book_content = self.state.get("book_content", [])
            curated_sources = self.state.get("curated_sources", [])
            self.workspace.assemble_and_export(final_book_content, curated_sources)
            logging.info("\n✅ ¡Proceso de generación del libro completado exitosamente!")
            return self.researcher.llm_fast, self.writer.llm_heavy
        except Exception as e:
            logging.critical(f"Ha ocurrido un error inesperado en el orquestador: {e}", exc_info=True)
            sys.exit("El proceso ha sido detenido debido a un error crítico.")

    def resume(self, loaded_state):
        self.state = loaded_state
        logging.info("Reanudando proceso desde el estado cargado.")
        try:
            if not self.state.get("book_content"):
                logging.info("El primer borrador no está completo. Iniciando fase de escritura.")
                if not self.writer.execute(): return None, None
            
            logging.info("Borrador existente encontrado. Iniciando fase de refinamiento.")
            if not self.refiner.execute(): return None, None

            final_book_content = self.state.get("book_content", [])
            curated_sources = self.state.get("curated_sources", [])
            self.workspace.assemble_and_export(final_book_content, curated_sources)
            logging.info("\n✅ ¡Proceso de generación del libro completado exitosamente!")
            return self.researcher.llm_fast, self.writer.llm_heavy
        except Exception as e:
            logging.critical(f"Ha ocurrido un error inesperado durante la reanudación: {e}", exc_info=True)
            sys.exit("El proceso ha sido detenido debido a un error crítico.")