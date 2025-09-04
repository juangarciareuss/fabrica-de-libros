# book_generator/phase_writing.py

import logging
import json
import config
from .llm_handler import LLMHandler

class PhaseWriting:
    """
    Gestiona la escritura del borrador delegando a especialistas y utilizando un
    filtro de contexto para optimizar el consumo de tokens.
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
        logging.info("\n--- [FASE 2] ESTRUCTURA Y ESCRITURA CON ESPECIALISTAS ---")
        topic = self.state["core_topic"]
        description = self.state["description"]
        topics_to_avoid = self.state["topics_to_avoid"]
        
        if not self.state.get("table_of_contents"):
            logging.info("No se encontró tabla de contenidos. Generando una nueva...")
            table_of_contents, _ = self.llm_fast.call_agent(
                "structuring_toc_generator",
                topic=topic, 
                book_description=description
            )
            if not table_of_contents:
                logging.error("No se pudo generar la tabla de contenidos. Abortando fase de escritura.")
                return False
            self.state["table_of_contents"] = table_of_contents
        
        table_of_contents = self.state["table_of_contents"]
        structured_research = self.workspace.load_structured_research()
        if not structured_research:
            logging.error("No se encontró la investigación estructurada. Abortando fase de escritura.")
            return False

        book_content = self.state.get("book_content", [])
        start_chapter_index = len(book_content)

        if start_chapter_index >= len(table_of_contents):
            logging.info("Todos los capítulos ya están escritos. Saltando la fase de escritura.")
            return True

        for i, chapter_data in enumerate(table_of_contents):
            if i < start_chapter_index:
                continue

            title = chapter_data.get('title')
            ctype = chapter_data.get('chapter_type')
            focus = chapter_data.get('focus')
            
            logging.info(f"Procesando capítulo {i+1}/{len(table_of_contents)}: '{title}' (Tipo: '{ctype}')")
            
            logging.info(f"  -> Activando Filtro de Contexto Inteligente para el enfoque: '{focus}'")
            contextual_summary, _ = self.llm_fast.call_agent(
                "structuring_context_summarizer",
                chapter_focus=focus,
                contextual_summary=json.dumps(structured_research, ensure_ascii=False)
            )
            if not contextual_summary:
                logging.warning("El Filtro de Contexto no devolvió información. Se usará el dossier completo como fallback.")
                contextual_summary = json.dumps(structured_research, ensure_ascii=False)

            agent_map = {
                'introduction': 'writer_introduction',
                'conclusion': 'writer_conclusion',
                'foundational_knowledge': 'writer_foundational',
                'practical_tutorial': 'writer_tutorial',
                'extended_use_cases': 'writer_use_cases',
                'competitor_comparison': 'writer_comparison'
            }
            agent_id = agent_map.get(ctype, 'writer_generic_fallback')

            common_args = {
                "book_topic": topic, 
                "chapter_title": title, 
                "chapter_focus": focus, 
                "topics_to_avoid": topics_to_avoid,
                "contextual_summary": contextual_summary
            }

            content, _ = self.llm_heavy.call_agent(agent_id, **common_args)

            if content and isinstance(content, str) and len(content.strip()) > 0:
                book_content.append({"title": title, "content": content, "type": ctype})
                self.workspace.save_chapter(i + 1, title, content)
            else:
                logging.warning(f"No se pudo generar contenido para el capítulo '{title}'. Se guardará como None.")
                book_content.append({"title": title, "content": None, "type": ctype})
            
            self.state['book_content'] = book_content
            self.workspace.save_progress(self.state)
        
        logging.info("✅ Fase de escritura con especialistas completada exitosamente.")
        return True