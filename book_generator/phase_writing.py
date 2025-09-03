# book_generator/phase_writing.py

import logging
import sys
import json
import config
import re
from .llm_handler import LLMHandler
from .researcher import research, get_text_from_url

class PhaseWriting:
    """Gestiona la escritura del borrador delegando a especialistas y manejando investigación dinámica."""
    
    # <<< MEJORA: El __init__ ahora acepta el logger y el manifest para la auditoría >>>
    def __init__(self, state, workspace, performance_logger, agent_manifest):
        self.state = state
        self.workspace = workspace
        self.performance_logger = performance_logger
        self.agent_manifest = agent_manifest
        
        # Pasamos el logger y manifest a los handlers para que puedan registrar el desempeño
        handler_args = {
            "performance_logger": self.performance_logger,
            "agent_manifest": self.agent_manifest
        }
        self.llm_fast = LLMHandler(config.API_KEY, config.FAST_MODEL_NAME, **handler_args)
        self.llm_heavy = LLMHandler(config.API_KEY, config.HEAVY_MODEL_NAME, **handler_args)

    def _handle_dynamic_research(self, chapter_content):
        # ... (este método no necesita cambios, ya está bien optimizado) ...
        # (Lo he omitido aquí por brevedad, pero debe estar en tu archivo final)
        pass # Reemplaza este 'pass' con tu código de _handle_dynamic_research

    def execute(self):
        logging.info("\n--- [FASE 2] ESTRUCTURA Y ESCRITURA CON ESPECIALISTAS ---")
        topic = self.state["core_topic"]
        description = self.state["description"]
        topics_to_avoid = self.state["topics_to_avoid"]
        
        table_of_contents, _ = self.llm_fast.generate_table_of_contents(topic=topic, book_description=description)
        if not table_of_contents:
            logging.error("Fallo en la arquitectura: no se pudo generar la tabla de contenidos.")
            return False
        
        self.state["table_of_contents"] = table_of_contents
        
        structured_research = self.workspace.load_structured_research()
        if not structured_research:
            logging.error("No se encontró la investigación estructurada. No se puede escribir.")
            return False

        # <<< OPTIMIZACIÓN: "Dispatch Table" de Especialistas >>>
        # Este diccionario mapea el tipo de capítulo al agente escritor y al contexto que necesita.
        writer_specialists = {
            'foundational_knowledge': {
                'method': self.llm_heavy.write_foundational_chapter,
                'context_keys': ['core_concepts', 'technical_details']
            },
            'practical_tutorial': {
                'method': self.llm_heavy.write_practical_tutorial_chapter,
                'context_keys': ['use_cases', 'technical_details']
            },
            'extended_use_cases': {
                'method': self.llm_heavy.write_use_cases_chapter,
                'context_keys': ['use_cases']
            },
            'competitor_comparison': {
                'method': self.llm_heavy.write_comparison_chapter,
                'context_keys': ['competitor_comparison', 'expert_opinions']
            }
            # Añadir nuevos especialistas aquí es tan simple como añadir una nueva entrada
        }

        book_content = self.state.get("book_content", [])
        start_chapter_index = len(book_content)

        if start_chapter_index >= len(table_of_contents):
            logging.info("Todos los capítulos ya están escritos. Saltando la fase de escritura.")
            return True

        for i, chapter_data in enumerate(table_of_contents):
            if i < start_chapter_index:
                continue

            title, ctype, focus = chapter_data.get('title'), chapter_data.get('chapter_type'), chapter_data.get('focus')
            logging.info(f"Asignando capítulo {i+1}/{len(table_of_contents)}: '{title}' (Tipo: '{ctype}')")
            
            content = None
            
            # --- LÓGICA DE DELEGACIÓN OPTIMIZADA ---
            specialist = writer_specialists.get(ctype)

            common_args = {
                "book_topic": topic, 
                "chapter_title": title, 
                "chapter_focus": focus, 
                "topics_to_avoid": topics_to_avoid,
                "chapter_type": ctype  # <<< AÑADE ESTA LÍNEA
            }

            if specialist:
                # Construye el contexto dinámicamente para el especialista
                context = {key: structured_research.get(key, []) for key in specialist['context_keys']}
                common_args['context'] = context
                content, _ = specialist['method'](**common_args)

            elif ctype in ['introduction', 'conclusion']:
                # Casos especiales que usan un resumen de todo
                context_summary, _ = self.llm_fast.get_contextual_summary(master_context=structured_research, **common_args)
                common_args['contextual_summary'] = context_summary
                if ctype == 'introduction':
                    common_args['book_description'] = description
                    content, _ = self.llm_heavy.write_introduction(**common_args)
                else: # conclusion
                    common_args['book_description'] = description
                    content, _ = self.llm_heavy.write_conclusion(**common_args)
            
            else: # Fallback para tipos no reconocidos
                logging.warning(f"No se encontró un escritor especialista para '{ctype}'. Usando el genérico.")
                context_summary, _ = self.llm_fast.get_contextual_summary(master_context=structured_research, **common_args)
                common_args['contextual_summary'] = context_summary
                content, _ = self.llm_heavy.write_chapter(**common_args)

            if content:
                content = self._handle_dynamic_research(content)
                book_content.append({"title": title, "content": content, "type": ctype})
                self.workspace.save_chapter(i + 1, title, content)
                self.state['book_content'] = book_content
                self.workspace.save_progress(self.state)
            else:
                logging.warning(f"No se pudo generar contenido para el capítulo '{title}'.")
        
        logging.info("Fase de escritura con especialistas completada exitosamente.")
        return True