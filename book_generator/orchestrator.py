# book_generator/orchestrator.py

import logging
import sys
import json
import os
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

    def _load_state_from_workspace(self):
        """Carga el estado desde el archivo progress.json del workspace."""
        loaded_state = self.workspace.load_progress()
        if loaded_state:
            self.state = loaded_state
            logging.info("Estado del proyecto cargado exitosamente desde 'progress.json'.")
            return True
        logging.error("No se pudo cargar 'progress.json'. No se puede reanudar.")
        return False

    def _execute_phases(self, run_research=True, run_writing=True, run_refinement=True):
        """Motor de ejecución centralizado para las fases."""
        try:
            if run_research:
                if not self.researcher.execute():
                    logging.critical("La fase de investigación falló. Abortando.")
                    return None, None
            
            if run_writing:
                if not self.writer.execute():
                    logging.critical("La fase de escritura falló. Abortando.")
                    return None, None
            
            if run_refinement:
                if not self.refiner.execute():
                    logging.critical("La fase de refinamiento falló. Abortando.")
                    return None, None
            
            final_book_content = self.state.get("book_content", [])
            curated_sources = self.state.get("curated_sources", [])
            self.workspace.assemble_and_export(final_book_content, curated_sources)
            logging.info("\n✅ ¡Proceso de generación del libro completado exitosamente!")
            
            # Devuelve los handlers del último módulo ejecutado para el reporte de costos
            if run_refinement: return self.refiner.llm_fast, self.refiner.llm_heavy
            if run_writing: return self.writer.llm_fast, self.writer.llm_heavy
            if run_research: return self.researcher.llm_fast, self.researcher.llm_heavy

        except Exception as e:
            logging.critical(f"Ha ocurrido un error inesperado en el orquestador: {e}", exc_info=True)
            sys.exit("El proceso ha sido detenido debido a un error crítico.")
        return None, None

    def run_full_process(self):
        """Ejecuta el pipeline completo para un nuevo libro."""
        logging.info("Iniciando un nuevo proceso de libro completo.")
        return self._execute_phases(True, True, True)

    def resume_from_last_state(self):
        """Reanuda el proceso basándose en el estado guardado."""
        if not self._load_state_from_workspace(): return None, None
        
        is_research_done = self.state.get("research_catalog") is not None
        is_writing_done = self.state.get("book_content") and all(c.get("content") for c in self.state["book_content"])

        if not is_research_done:
            logging.info("La investigación no está completa. Reanudando desde la fase de investigación.")
            return self._execute_phases(True, True, True)
        elif not is_writing_done:
            logging.info("La escritura no está completa. Reanudando desde la fase de escritura.")
            return self._execute_phases(False, True, True)
        else:
            logging.info("La investigación y escritura están completas. Reanudando desde la fase de refinamiento.")
            return self._execute_phases(False, False, True)

    def run_from_phase(self, phase_key):
        """Inicia el proceso desde una fase específica seleccionada por el usuario."""
        if not self._load_state_from_workspace(): return None, None

        if phase_key == 'a':
            logging.info("Re-lanzando desde la FASE DE INVESTIGACIÓN.")
            # Limpiar datos de investigación y escritura para empezar de nuevo
            self.state["research_catalog"] = None
            self.state["book_content"] = []
            self.state["table_of_contents"] = None
            for f in os.listdir(self.workspace.workspace_dir):
                if f.endswith(".md"): os.remove(os.path.join(self.workspace.workspace_dir, f))
            return self._execute_phases(True, True, True)
        
        elif phase_key == 'b':
            logging.info("Re-lanzando desde la FASE DE ESCRITURA.")
            if not self.state.get("research_catalog"):
                logging.error("No se puede iniciar desde la escritura, falta la investigación. Ejecuta la investigación primero.")
                return None, None
            # Limpiar solo los capítulos para volver a escribirlos
            self.state["book_content"] = []
            for f in os.listdir(self.workspace.workspace_dir):
                if f.endswith(".md"): os.remove(os.path.join(self.workspace.workspace_dir, f))
            return self._execute_phases(False, True, True)
            
        elif phase_key == 'c':
            logging.info("Re-lanzando desde la FASE DE REFINAMIENTO.")
            if not self.state.get("book_content"):
                logging.error("No se puede iniciar desde el refinamiento, faltan los capítulos. Ejecuta la escritura primero.")
                return None, None
            return self._execute_phases(False, False, True)
        
        else:
            logging.error("Clave de fase no reconocida.")
            return None, None