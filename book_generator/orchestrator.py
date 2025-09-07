# book_generator/orchestrator.py

import logging
import sys
import json
import os
from .workspace_manager import WorkspaceManager
from .phase_research import PhaseResearch
from .phase_writing import PhaseWriting
from .phase_audit import PhaseAudit
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
        self.auditor = PhaseAudit(**common_args)
        self.refiner = PhaseRefinement(**common_args)

        logging.info(f"Orquestador inicializado. Workspace en: '{self.workspace.workspace_dir}'")
    
    # --- !! MÉTODO NUEVO Y CLAVE !! ---
    def analyze_youtube_content(self):
        """
        Activa el agente analista para que revise el contenido de Youtube.txt
        y proponga un nuevo capítulo para el libro.
        """
        # El workspace se encarga de leer el archivo de forma segura
        transcript = self.workspace.read_youtube_transcript("Youtube.txt")
        if not transcript:
            logging.warning("No se encontró contenido en Youtube.txt para analizar.")
            return None
            
        # Usamos el LLM rápido para esta tarea de análisis estratégico
        proposed_chapter, _ = self.writer.llm_fast.call_agent(
            "youtube_analyst",
            youtube_transcript=transcript
        )
        return proposed_chapter

    def _update_phase_handlers_state(self):
        self.researcher.state = self.state
        self.writer.state = self.state
        self.auditor.state = self.state
        self.refiner.state = self.state
        logging.info("El estado interno de todas las fases ha sido sincronizado.")

    def _load_state_from_workspace(self):
        loaded_state = self.workspace.load_progress()
        if loaded_state:
            self.state = loaded_state
            self._update_phase_handlers_state()
            logging.info("Estado del proyecto cargado y sincronizado exitosamente.")
            return True
        logging.error("No se pudo cargar 'progress.json'. No se puede reanudar.")
        return False

    def _execute_phases(self, run_research=True, run_writing=True, run_audit=True, run_refinement=True):
        try:
            if run_research:
                if not self.researcher.execute(): return None, None
            if run_writing:
                if not self.writer.execute(): return None, None
            if run_audit:
                if not self.auditor.execute(): return None, None
            if run_refinement:
                if not self.refiner.execute(): return None, None
            
            final_book_content = self.state.get("book_content", [])
            curated_sources = self.state.get("curated_sources", [])
            self.workspace.assemble_and_export(final_book_content, curated_sources)
            logging.info("\n✅ ¡Proceso de generación del libro completado exitosamente!")
            
            if run_refinement: return self.refiner.llm_fast, self.refiner.llm_heavy
            if run_audit: return self.auditor.llm_fast, self.auditor.llm_heavy
            if run_writing: return self.writer.llm_fast, self.writer.llm_heavy
            if run_research: return self.researcher.llm_fast, self.researcher.llm_heavy
        except Exception as e:
            logging.critical(f"Ha ocurrido un error inesperado en el orquestador: {e}", exc_info=True)
            sys.exit("El proceso ha sido detenido debido a un error crítico.")
        return None, None

    def run_full_process(self, youtube_chapter_data=None):
        logging.info("Iniciando un nuevo proceso de libro completo.")
        
        if youtube_chapter_data:
            if not self.state.get("table_of_contents"):
                base_toc, _ = self.writer.llm_fast.call_agent(
                    "structuring_toc_generator",
                    topic=self.state["core_topic"], 
                    book_description=self.state["description"]
                )
                self.state["table_of_contents"] = base_toc if base_toc else []
            
            if self.state["table_of_contents"]:
                insertion_point = next((i + 1 for i, chap in enumerate(self.state["table_of_contents"]) if chap.get('chapter_type') == 'practical_tutorial'), -1)
                if insertion_point != -1:
                    self.state["table_of_contents"].insert(insertion_point, youtube_chapter_data)
                else:
                    self.state["table_of_contents"].insert(-1, youtube_chapter_data)
                logging.info(f"Capítulo de YouTube '{youtube_chapter_data['title']}' insertado en la estructura del libro.")

        return self._execute_phases(True, True, True, True)

    def resume_from_last_state(self):
        if not self._load_state_from_workspace(): return None, None
        
        is_research_done = self.state.get("research_catalog") is not None
        is_writing_done = self.state.get("book_content") and all(c.get("content") for c in self.state["book_content"])
        is_audit_done = os.path.exists(os.path.join(self.workspace.workspace_dir, "audit_report.json"))

        if not is_research_done:
            return self._execute_phases(True, True, True, True)
        elif not is_writing_done:
            return self._execute_phases(False, True, True, True)
        elif not is_audit_done:
            return self._execute_phases(False, False, True, True)
        else:
            return self._execute_phases(False, False, False, True)

    def run_from_phase(self, phase_key):
        if not self._load_state_from_workspace(): return None, None

        if phase_key == 'a':
            self.state.update({"research_catalog": None, "book_content": [], "table_of_contents": None})
            self._update_phase_handlers_state()
            for f in os.listdir(self.workspace.workspace_dir):
                if f.endswith((".md", ".json")) and "performance_log" not in f: 
                    os.remove(os.path.join(self.workspace.workspace_dir, f))
            return self._execute_phases(True, True, True, True)
        
        elif phase_key == 'b':
            if not self.state.get("research_catalog"):
                logging.error("No se puede iniciar desde la escritura, falta la investigación.")
                return None, None
            self.state["book_content"] = []
            if 'audit_report' in self.state: del self.state['audit_report']
            self._update_phase_handlers_state() 
            for f in os.listdir(self.workspace.workspace_dir):
                if f.endswith(".md") or f == "audit_report.json":
                    os.remove(os.path.join(self.workspace.workspace_dir, f))
            logging.info("Estado y archivos de capítulos anteriores eliminados. Iniciando re-escritura...")
            return self._execute_phases(False, True, True, True)
            
        elif phase_key == 'c':
            if not self.state.get("book_content"):
                logging.error("No se puede iniciar desde el refinamiento, faltan los capítulos.")
                return None, None
            return self._execute_phases(False, False, False, True)
        
        else:
            logging.error("Clave de fase no reconocida.")
            return None, None