import logging
import sys
import os
import json
import re
from datetime import datetime
import config
from .researcher import perform_research_plan, get_text_from_url
from .llm_handler import LLMHandler
from .book_assembler import create_word_document, convert_to_epub

class BookOrchestrator:
    """
    Encapsula toda la lógica de orquestación para la creación de un libro,
    incluyendo la generación de informes de crítica visibles en cada ciclo.
    """
    def __init__(self, core_topic, description):
        self.core_topic = core_topic
        self.description = description
        self.llm_fast = LLMHandler(api_key=config.API_KEY, model_name=config.FAST_MODEL_NAME)
        self.llm_heavy = LLMHandler(api_key=config.API_KEY, model_name=config.HEAVY_MODEL_NAME)
        self.safe_title = "".join(x for x in self.core_topic if x.isalnum() or x in " _-").strip().replace(" ", "_")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.workspace_dir = os.path.join("workspace", f"{self.safe_title}_{self.timestamp}")
        os.makedirs(self.workspace_dir, exist_ok=True)
        logging.info(f"Espacio de trabajo creado en: '{self.workspace_dir}'")

    def run(self):
        # --- NUEVA ARQUITECTURA DE INVESTIGACIÓN EN DOS FASES ---
        logging.info("\n--- [FASE 1] INTELIGENCIA DE ACTUALIDAD (ÚLTIMOS 30 DÍAS) ---")
        news_plan = self.llm_fast.plan_research(self.core_topic, self.description, research_type='recent_news')
        recent_sources = perform_research_plan(news_plan['queries'], date_restrict='m1') if news_plan else []

        logging.info("\n--- [FASE 2] INVESTIGACIÓN DE CONTEXTO PROFUNDO (ÚLTIMOS 5 AÑOS) ---")
        context_plan = self.llm_fast.plan_research(self.core_topic, self.description, research_type='deep_context')
        deep_sources = perform_research_plan(context_plan['queries'], date_restrict='y5') if context_plan else []

        # Combinamos y de-duplicamos todas las fuentes encontradas
        all_found_sources = list({s['link']: s for s in recent_sources + deep_sources}.values())
        self._save_full_research_to_workspace(all_found_sources)

        if not self._quality_gate_passed(len(all_found_sources)):
            sys.exit("Proceso terminado para garantizar la calidad.")

        logging.info("\n--- [ETAPA 3/7] CURACIÓN Y SÍNTESIS ---")
        curated_sources = self.llm_fast.evaluate_sources(self.core_topic, self.description, all_found_sources)
        if not curated_sources: sys.exit("Fallo en la curación.")
        
        self._save_bibliography_to_workspace(curated_sources)
        research_catalog = self._build_research_catalog(curated_sources)
        
        table_of_contents = self.llm_fast.generate_table_of_contents(self.core_topic, self.description)
        if not table_of_contents: sys.exit("Fallo en la arquitectura.")
        
        book_content = self._write_draft(table_of_contents, research_catalog)
        refined_content = self._refine_draft(book_content, research_catalog)
        self._generate_fact_check_report(refined_content, curated_sources)
        self._assemble_and_export(refined_content, curated_sources)
        
        return self.llm_fast, self.llm_heavy

    def _quality_gate_passed(self, num_sources):
        logging.info(f"\n--- PUERTA DE CALIDAD BIBLIOGRÁFICA ---")
        if num_sources >= config.MIN_SOURCES_FOR_BOOK:
            logging.info(f"✅ ÉXITO: {num_sources} fuentes encontradas (mínimo: {config.MIN_SOURCES_FOR_BOOK}).")
            return True
        else:
            logging.error(f"❌ FALLO: Solo se encontraron {num_sources} fuentes (mínimo: {config.MIN_SOURCES_FOR_BOOK}).")
            return False

    def _save_full_research_to_workspace(self, all_sources):
        """Guarda la lista COMPLETA de fuentes encontradas."""
        try:
            filepath = os.path.join(self.workspace_dir, "full_research_bibliography.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(all_sources, f, indent=4, ensure_ascii=False)
            logging.info(f"  -> 📚 Bibliografía completa ({len(all_sources)} fuentes) guardada en: '{filepath}'")
        except Exception as e:
            logging.error(f"No se pudo guardar la bibliografía completa: {e}")

    def _save_bibliography_to_workspace(self, curated_sources):
        """Guarda la lista de fuentes curadas en el espacio de trabajo."""
        try:
            filepath = os.path.join(self.workspace_dir, "bibliography.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(curated_sources, f, indent=4, ensure_ascii=False)
            logging.info(f"  -> 📚 Bibliografía curada guardada exitosamente en: '{filepath}'")
        except Exception as e:
            logging.error(f"No se pudo guardar la bibliografía: {e}")

    def _build_research_catalog(self, curated_sources):
        """Crea el catálogo estructurado de investigación."""
        catalog = []
        for i, source in enumerate(curated_sources):
            # Asignamos el ID aquí para que sea consistente a través de todo el sistema
            curated_sources[i]['id'] = i + 1
            content = get_text_from_url(source['url'])
            if content:
                catalog.append({"id": i + 1, "url": source['url'], "title": source['title'], "content": content})
        return catalog

    def _write_draft(self, toc, research_catalog):
        """Maneja la etapa 4: Redacción del borrador inicial."""
        book_content = []
        for i, chapter_data in enumerate(toc):
            title, type, focus = chapter_data.get('title'), chapter_data.get('chapter_type'), chapter_data.get('focus')
            summary = self.llm_fast.get_contextual_summary(self.core_topic, title, focus, type, research_catalog)
            content = None
            if type == 'introduction': content = self.llm_heavy.write_introduction(self.core_topic, self.description, summary)
            elif type == 'conclusion': content = self.llm_heavy.write_conclusion(self.core_topic, self.description, summary)
            elif type == 'extended_use_cases': content = self.llm_heavy.write_extended_use_cases(self.core_topic, self.description, title, focus, summary)
            else: content = self.llm_heavy.write_chapter(self.core_topic, self.description, title, type, focus, summary)
            if content:
                book_content.append({"title": title, "content": content, "type": type})
                self._save_chapter_to_workspace(i + 1, title, content)
        return book_content

    def _refine_draft(self, book_content, research_catalog):
        """
        Maneja la etapa 5: Ciclos de crítica y refactorización, con informes de progreso visibles.
        """
        for cycle in range(config.MAX_REFINEMENT_CYCLES):
            logging.info(f"\n--- Ciclo de Refinamiento: Ronda {cycle + 1}/{config.MAX_REFINEMENT_CYCLES} ---")
            critique = self.llm_fast.critique_book(self.core_topic, self.description, book_content)
            if not critique:
                logging.warning("El Agente Crítico no pudo generar un informe en esta ronda.")
                break

            print("\n--- 📜 INFORME DEL AGENTE CRÍTICO (RONDA {}) 📜 ---".format(cycle + 1))
            chapters_to_refine = []
            for i, report in enumerate(critique):
                score = report.get('score', 0)
                status = "✅ CUMPLE" if score >= config.MIN_SCORE_FOR_APPROVAL else "❌ REQUIERE MEJORA"
                print(f"Capítulo: {report.get('chapter_title', 'N/A')} | Puntuación: {score}/10 | {status}")
                if status == "❌ REQUIERE MEJORA":
                    print(f"  └─ Orden de Mejora: {report.get('improvement_needed', 'N/A')}")
                    chapters_to_refine.append((i, report))
            print("--------------------------------------------------\n")

            if not chapters_to_refine:
                logging.info("🎉 Todos los capítulos cumplen con el estándar de calidad. Proceso de refinamiento completado.")
                break
            
            logging.info(f"Se refinarán {len(chapters_to_refine)} capítulos con baja puntuación.")
            for index, report in chapters_to_refine:
                chapter = book_content[index]
                summary = self.llm_fast.get_contextual_summary(self.core_topic, chapter['title'], report.get('improvement_needed',''), chapter['type'], research_catalog)
                new_content = self.llm_heavy.refactor_chapter(chapter['title'], chapter['content'], report['improvement_needed'], summary)
                if new_content:
                    book_content[index]['content'] = new_content
                    self._save_chapter_to_workspace(index + 1, chapter['title'], new_content)
        return book_content

    def _generate_fact_check_report(self, book_content, curated_sources):
        """Crea el informe de verificación de hechos."""
        logging.info("\n--- [NUEVA ETAPA] GENERANDO INFORME DE VERIFICACIÓN DE HECHOS ---")
        report = []
        for chapter in book_content:
            chapter_report = {"chapter_title": chapter['title'], "fact_checks": []}
            paragraphs = [p for p in chapter['content'].split('\n') if p.strip()]
            for i, para in enumerate(paragraphs):
                cite_matches = re.findall(r'<!-- CITE:\s*([\d,\s]+) -->', para)
                if cite_matches:
                    clean_para = re.sub(r'<!-- CITE:.*?-->', '', para).strip()
                    source_ids = [int(s.strip()) for match in cite_matches for s in match.split(',')]
                    source_urls = [s['url'] for s in curated_sources if s.get('id') in source_ids]
                    chapter_report['fact_checks'].append({
                        "paragraph_index": i + 1,
                        "text_snippet": clean_para,
                        "source_ids": source_ids,
                        "source_urls": source_urls
                    })
            report.append(chapter_report)
        try:
            filepath = os.path.join(self.workspace_dir, "fact_check_report.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=4, ensure_ascii=False)
            logging.info(f"  -> ✅ Informe de verificación guardado en: '{filepath}'")
        except Exception as e:
            logging.error(f"No se pudo guardar el informe de verificación: {e}")

    def _save_chapter_to_workspace(self, index, title, content):
        """Guarda el contenido de un capítulo en el espacio de trabajo."""
        try:
            safe_chapter_title = "".join(x for x in title if x.isalnum() or x in " _-").strip().replace(" ", "_")
            filename = f"{index:02d}_{safe_chapter_title}.md"
            filepath = os.path.join(self.workspace_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n{content}")
            logging.info(f"  -> 💾 Progreso guardado en: '{filepath}'")
        except Exception as e:
            logging.error(f"No se pudo guardar el capítulo '{title}': {e}")
            
    def _assemble_and_export(self, book_content, curated_sources):
        """Maneja las etapas 6 y 7: Ensamblaje y exportación."""
        final_book_title = f"{self.safe_title}_{self.timestamp}"
        docx_path = create_word_document(final_book_title, book_content, curated_sources, output_folder=self.workspace_dir)
        epub_path = convert_to_epub(docx_path, final_book_title, output_folder=self.workspace_dir)

        print(f"\n✅ ¡Proceso Completado! Documentos finales guardados en '{self.workspace_dir}'")
        if docx_path: print(f"✔️ Documento Word: {docx_path}")
        if epub_path: print(f"✔️ Archivo EPUB: {epub_path}")

