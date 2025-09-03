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
    def __init__(self, core_topic, description, domain, topics_to_avoid, initial_queries=None, workspace_path=None):
        self.state = {
            "core_topic": core_topic, "description": description, "domain": domain,
            "topics_to_avoid": topics_to_avoid, "book_content": [], "research_catalog": None,
            "youtube_transcript": None, "curated_sources": None, "table_of_contents": None,
            "web_queries": initial_queries
        }
        
        self.workspace = WorkspaceManager(core_topic, existing_path=workspace_path)
        
        with open('agent_manifest.json', 'r', encoding='utf-8') as f:
            self.agent_manifest = {agent['agent_id']: agent for agent in json.load(f)['agents']}
        
        self.performance_logger = PerformanceLogger(self.workspace.workspace_dir)

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

    def resume(self, workspace_path):
        self.workspace = WorkspaceManager(self.state.get('core_topic', ''), existing_path=workspace_path)
        loaded_state = self.workspace.load_progress()
        if not loaded_state:
            logging.error("El directorio de trabajo existe pero no se pudo cargar 'progress.json'. No se puede reanudar.")
            return

        self.state = loaded_state
        logging.info("Reanudando proceso desde el estado cargado.")
        
        try:
            writing_complete = all(chapter.get("content") for chapter in self.state.get("book_content", []))

            if not writing_complete:
                logging.info("El primer borrador no está completo. Reanudando fase de escritura.")
                if not self.writer.execute(): return None, None
            
            logging.info("Borrador existente encontrado. Reanudando fase de refinamiento.")
            if not self.refiner.execute(): return None, None

            final_book_content = self.state.get("book_content", [])
            curated_sources = self.state.get("curated_sources", [])
            self.workspace.assemble_and_export(final_book_content, curated_sources)
            logging.info("\n✅ ¡Proceso de generación del libro completado exitosamente!")
            
            return self.refiner.llm_fast, self.refiner.llm_heavy
            
        except Exception as e:
            logging.critical(f"Ha ocurrido un error inesperado durante la reanudación: {e}", exc_info=True)
            sys.exit("El proceso ha sido detenido debido a un error crítico.")