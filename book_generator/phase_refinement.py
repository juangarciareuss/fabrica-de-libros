# book_generator/phase_refinement.py

import logging
import json
import config
from .llm_handler import LLMHandler

class PhaseRefinement:
    """
    Gestiona un ciclo completo de crítica y reescritura del borrador, optimizado
    para un consumo mínimo de tokens y máxima mantenibilidad.
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

    def _get_critique_for_chapter(self, chapter):
        """Llama al crítico especialista adecuado usando el despachador de agentes."""
        ctype = chapter.get('type')
        logging.info(f" -> Asignando '{chapter['title']}' (Tipo: {ctype}) al crítico especialista...")

        agent_map = {
            'practical_tutorial': 'critic_tutorial',
            'foundational_knowledge': 'critic_foundational',
            'extended_use_cases': 'critic_use_cases',
            'competitor_comparison': 'critic_comparison'
        }
        agent_id = agent_map.get(ctype, 'critic_generic_fallback')

        return self.llm_fast.call_agent(agent_id, chapter_title=chapter['title'], chapter_text=chapter['content'])

    def _refactor_chapter(self, chapter, report):
        """
        Llama al refactorizador especialista adecuado sin contexto de investigación
        para máxima eficiencia de costos.
        """
        ctype = chapter.get('type')
        logging.info(f" -> Refactorizando '{chapter['title']}' con especialista (Tipo: {ctype})...")

        agent_map = {
            'practical_tutorial': 'refactor_tutorial',
            'foundational_knowledge': 'refactor_foundational',
            'extended_use_cases': 'refactor_use_cases',
            'competitor_comparison': 'refactor_comparison'
        }
        agent_id = agent_map.get(ctype, 'refactor_generic_fallback')

        refactor_args = {
            "chapter_title": chapter['title'],
            "original_content": chapter['content'],
            "critique_feedback": json.dumps(report.get('paragraph_critiques', []), indent=2, ensure_ascii=False),
            "user_feedback": report.get('user_feedback', 'N/A'),
            "topics_to_avoid": self.state.get("topics_to_avoid", [])
        }
        
        return self.llm_heavy.call_agent(agent_id, **refactor_args)

    def execute(self):
        logging.info("\n--- [FASE 4] REFINAMIENTO INTERACTIVO ---")
        
        book_content = self.state.get("book_content", [])
        if not book_content:
            logging.warning("No se encontró contenido de libro para refinar. Saltando fase.")
            return True

        print("\n" + "="*80)
        logging.info("INICIANDO CICLO DE REFINAMIENTO COMPLETO")
        print("="*80)
        
        chapters_to_refine = []
        
        print("\n--- [PASO 4.1] RONDA DE REVISIÓN EDITORIAL ---")
        for i, chapter in enumerate(book_content):
            if not chapter.get('content') or not isinstance(chapter.get('content'), str) or len(chapter.get('content').strip()) < 50:
                logging.warning(f"Saltando crítica de '{chapter.get('title', 'N/A')}' por falta de contenido.")
                continue

            print(f"\n[DIAGNÓSTICO] Llamando al agente crítico para el capítulo {i+1}: '{chapter.get('title', 'N/A')}'...")
            critique, _ = self._get_critique_for_chapter(chapter)
            if not critique:
                logging.warning(f"El crítico no devolvió feedback para '{chapter.get('title', 'N/A')}'.")
                continue

            print(f"[REVISANDO] '{chapter.get('title', 'N/A')}' | Puntuación IA: {critique.get('overall_score', 0)}/10")
            print(f"  └─ Resumen (IA): {critique.get('general_feedback', 'N/A')}")
            
            user_feedback = input("  => ¿Tu orden de mejora? (Enter para omitir): ").strip()
            critique['user_feedback'] = user_feedback
            
            score = critique.get('overall_score')
            if (score is not None and score < config.MIN_SCORE_FOR_APPROVAL) or user_feedback:
                logging.info(f"'{chapter.get('title', 'N/A')}' MARCADO para refactorización.")
                chapters_to_refine.append((i, critique))
        
        if not chapters_to_refine:
            logging.info("\n🎉 ¡PROCESO DE REVISIÓN FINALIZADO! Ningún capítulo fue marcado para mejoras.")
        else:
            print("\n--- [PASO 4.2] APLICANDO MEJORAS DE REFACTORIZACIÓN ---")
            logging.info(f"Se refinarán {len(chapters_to_refine)} capítulos.")
            
            for index, report in chapters_to_refine:
                chapter_to_refactor = book_content[index]
                new_content_data, _ = self._refactor_chapter(chapter_to_refactor, report)

                if new_content_data and new_content_data.get('rewritten_chapter'):
                    self.state["book_content"][index]['content'] = new_content_data['rewritten_chapter']
                    logging.info(f"Éxito al refactorizar '{chapter_to_refactor['title']}'.")
                    self.workspace.save_chapter(index + 1, chapter_to_refactor['title'], new_content_data['rewritten_chapter'])
                    self.workspace.save_progress(self.state)
                else:
                    logging.error(f"El refactorizador no pudo mejorar el capítulo '{chapter_to_refactor['title']}'.")

        logging.info("\n✅ Fase de refinamiento completada exitosamente.")
        return True