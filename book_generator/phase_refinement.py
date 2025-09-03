# book_generator/phase_refinement.py

import logging
import sys
import json
import config
from .llm_handler import LLMHandler

class PhaseRefinement:
    """
    Gestiona el ciclo iterativo de crítica y reescritura usando un comité
    de agentes críticos y refactorizadores especialistas.
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
        logging.info("\n--- [FASE 3] REFINAMIENTO DEL BORRADOR CON ESPECIALISTAS ---")
        book_content = self.state["book_content"]
        
        for cycle in range(config.MAX_REFINEMENT_CYCLES):
            logging.info(f"\n--- Ciclo de Refinamiento: Ronda {cycle + 1}/{config.MAX_REFINEMENT_CYCLES} ---")
            print("\n--- [PASO 3 de 3] REVISIÓN DE CAPÍTULOS POR EL COMITÉ EDITORIAL ---")
            
            chapters_to_refine = []
            total_score = 0
            chapters_critiqued_count = 0
            
            for i, chapter in enumerate(book_content):
                ctype = chapter.get('type')
                critique = None
                
                logging.info(f" -> Asignando '{chapter['title']}' (Tipo: {ctype}) al crítico especialista...")

                # --- LÓGICA DE DELEGACIÓN AL CRÍTICO ESPECIALISTA ---
                if ctype == 'practical_tutorial':
                    critique, _ = self.llm_fast.critique_tutorial_chapter(chapter_title=chapter['title'], chapter_text=chapter['content'])
                elif ctype == 'foundational_knowledge':
                    critique, _ = self.llm_fast.critique_foundational_chapter(chapter_title=chapter['title'], chapter_text=chapter['content'])
                elif ctype == 'extended_use_cases':
                    critique, _ = self.llm_fast.critique_use_cases_chapter(chapter_title=chapter['title'], chapter_text=chapter['content'])
                elif ctype == 'competitor_comparison':
                    critique, _ = self.llm_fast.critique_comparison_chapter(chapter_title=chapter['title'], chapter_text=chapter['content'])
                else: # Fallback al crítico general
                    logging.warning(f"No se encontró un crítico especialista para el tipo '{ctype}'. Usando el crítico genérico.")
                    critique, _ = self.llm_fast.critique_chapter(chapter_title=chapter['title'], chapter_text=chapter['content'])
                
                if not critique:
                    logging.warning(f"El agente crítico no devolvió feedback válido para '{chapter['title']}'.")
                    continue

                # <<< REGISTRO DE PUNTUACIÓN DE DESEMPEÑO >>>
                agent_id = f"critic_{ctype}" if ctype else "critic_generic_fallback"
                self.performance_logger.log(
                    agent_id=agent_id,
                    event_type="critique_score",
                    details={ "score_given": critique.get('overall_score', 0) }
                )

                # Visualización de la crítica para el usuario
                print(f"\n - Capítulo: {chapter.get('title', 'N/A')} | Puntuación IA: {critique.get('overall_score', 0)}/10")
                print(f"   └─ Resumen (IA): {critique.get('general_feedback', 'N/A')}")
                paragraph_critiques = critique.get('paragraph_critiques', [])
                if paragraph_critiques:
                    print("   └─ Órdenes Específicas:")
                    for pc in paragraph_critiques:
                        print(f"     - Párrafo #{pc.get('paragraph_number')}: {pc.get('feedback')}")
                print(f"   └─ Camino al 10/10 (IA): {critique.get('path_to_10', 'N/A')}")

                user_feedback = input("   => ¿Tu orden de mejora GENERAL para este capítulo? (deja en blanco para omitir): ")
                if user_feedback: critique['user_feedback'] = user_feedback
                
                total_score += critique.get('overall_score', 0)
                chapters_critiqued_count += 1

                if critique.get('overall_score', 0) < config.MIN_SCORE_FOR_APPROVAL or user_feedback:
                    chapters_to_refine.append((i, critique))

            if chapters_critiqued_count > 0:
                average_score = total_score / chapters_critiqued_count
                logging.info(f"\nEvaluación Global de la Ronda {cycle + 1}: Puntuación promedio del libro = {average_score:.2f}/10")

            if not chapters_to_refine:
                logging.info("🎉 ¡Decisión final! Ningún capítulo requiere refinamiento. Proceso completado.")
                break
            
            logging.info(f"Se refinarán {len(chapters_to_refine)} capítulos.")
            for index, report in chapters_to_refine:
                chapter = book_content[index]
                ctype = chapter.get('type')
                
                # --- LÓGICA DE DELEGACIÓN AL REFACTORIZADOR ESPECIALISTA ---
                # Preparamos los argumentos comunes
                refactor_args = {
                    "chapter_title": chapter['title'],
                    "original_content": chapter['content'],
                    "critique_feedback": json.dumps(report.get('paragraph_critiques', []), indent=2, ensure_ascii=False),
                    "user_feedback": report.get('user_feedback', 'N/A'),
                    "contextual_summary": self.state["research_catalog"],
                    "topics_to_avoid": self.state["topics_to_avoid"]
                }

                if ctype == 'practical_tutorial':
                     new_content_data, _ = self.llm_heavy.refactor_tutorial_chapter(**refactor_args)
                elif ctype == 'foundational_knowledge':
                    new_content_data, _ = self.llm_heavy.refactor_foundational_chapter(**refactor_args)
                elif ctype == 'extended_use_cases':
                    new_content_data, _ = self.llm_heavy.refactor_use_cases_chapter(**refactor_args)
                elif ctype == 'competitor_comparison':
                    new_content_data, _ = self.llm_heavy.refactor_comparison_chapter(**refactor_args)
                else: # Fallback
                    logging.warning(f"No se encontró un refactorizador especialista para el tipo '{ctype}'. Usando el genérico.")
                    new_content_data, _ = self.llm_heavy.refactor_chapter(**refactor_args)

                if new_content_data and new_content_data.get('rewritten_chapter'):
                    rewritten_content = new_content_data['rewritten_chapter']
                    if isinstance(rewritten_content, dict):
                        rewritten_content = rewritten_content.get('text', str(rewritten_content))
                    
                    final_content = str(rewritten_content)
                    book_content[index]['content'] = final_content
                    
                    logging.info(f"Justificación del Refactorizador para '{chapter['title']}': {new_content_data.get('justification', 'N/A')}")
                    self.workspace.save_chapter(index + 1, chapter['title'], final_content)
                    self.workspace.save_progress(self.state)

        self.state["book_content"] = book_content
        logging.info("Fase de refinamiento completada exitosamente.")
        return True

    def run_final_critique(self):
        """
        Ejecuta una ronda final de críticas sobre el contenido ya refinado para generar
        un informe de calidad definitivo, sin pedir feedback ni refactorizar.
        """
        logging.info("\n--- [FASE 4] INFORME DE CALIDAD FINAL ---")
        print("\nGenerando el informe de calidad final sobre la versión definitiva del libro...")
        book_content = self.state["book_content"]
        if not book_content:
            logging.warning("No hay contenido en el libro para generar una crítica final.")
            return

        total_score = 0
        for i, chapter in enumerate(book_content):
            ctype = chapter.get('type')
            critique, _ = self.llm_fast.critique_chapter(chapter_title=chapter['title'], chapter_text=chapter['content'])
            if not critique:
                logging.warning(f"El crítico no devolvió feedback para el capítulo final '{chapter['title']}'.")
                continue

            print(f"\n - Capítulo Final: {chapter.get('title', 'N/A')} | Puntuación Definitiva: {critique.get('overall_score', 0)}/10")
            print(f"   └─ Resumen (IA): {critique.get('general_feedback', 'N/A')}")
            print(f"   └─ Sugerencia Final para un 10/10 (IA): {critique.get('path_to_10', 'N/A')}")
            total_score += critique.get('overall_score', 0)

        if book_content:
            average_score = total_score / len(book_content)
            print("\n" + "="*70)
            logging.info(f"PUNTUACIÓN GLOBAL DEFINITIVA DEL LIBRO: {average_score:.2f} / 10")
            print("="*70)