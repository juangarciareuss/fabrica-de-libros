# book_generator/phase_research.py

import logging
import sys
import config
from .llm_handler import LLMHandler
from .researcher import research, get_text_from_url

class PhaseResearch:
    """Gestiona la fase de investigación: búsqueda, pre-selección y curación."""
    
    def __init__(self, state, workspace, performance_logger, agent_manifest):
        self.state = state
        self.workspace = workspace
        self.performance_logger = performance_logger
        self.agent_manifest = agent_manifest
        
        # Pasamos el logger y manifest al handler para que pueda registrar el desempeño
        self.llm_fast = LLMHandler(
            api_key=config.API_KEY, 
            model_name=config.FAST_MODEL_NAME,
            performance_logger=self.performance_logger,
            agent_manifest=self.agent_manifest
        )

    def _get_titles_for_urls(self, urls):
        """Intenta extraer un título simple de una lista de URLs."""
        with_titles = []
        for url in urls:
            try:
                title = url.split('/')[-1].replace('-', ' ').replace('_', ' ').title()
                if not title or len(title) < 5: title = "Artículo Relacionado"
                with_titles.append({"url": url, "title": title})
            except Exception:
                continue
        return with_titles

    def execute(self):
        logging.info("\n--- [FASE 1] RECOLECCIÓN Y PRE-SELECCIÓN ---")
        topic = self.state["core_topic"]
        description = self.state["description"]
        domain = self.state["domain"]
        
        web_queries_plan, _ = self.llm_fast.generate_web_queries(topic=topic, description=description)
        queries = web_queries_plan.get('queries', [topic]) if web_queries_plan else [topic]
        
        print("\n--- [PASO 1 de 3] REVISIÓN DE BÚSQUEDA ---")
        print(f"La IA ha generado estas consultas: {queries}")
        if input("¿Añadir más términos de búsqueda? (s/n): ").lower() == 's':
            extra_query = input("Añade tus términos, separados por comas: ")
            queries.extend([q.strip() for q in extra_query.split(',')])
            logging.info(f"Consultas actualizadas: {queries}")
            
        found_links = research(queries)
        links_with_titles = self._get_titles_for_urls(found_links)
        
        preselected_urls, _ = self.llm_fast.preselect_urls(topic=topic, domain=domain, found_links_with_titles=links_with_titles)
        if not preselected_urls:
            logging.error("El agente pre-selector no pudo elegir ninguna URL.")
            return False
        
        web_content_map = {link: get_text_from_url(link) for link in preselected_urls if get_text_from_url(link)}
        youtube_transcript = self.workspace.read_youtube_transcript()
        
        full_content = "\n".join(web_content_map.values()) + f"\n{youtube_transcript}"
        if not full_content.strip():
            logging.error("No se pudo recolectar contenido de las fuentes.")
            return False

        # --- LÓGICA DE PROCESAMIENTO POR LOTES (CHUNKING) ---
        chunk_size = 30000
        content_chunks = [full_content[i:i + chunk_size] for i in range(0, len(full_content), chunk_size)]
        logging.info(f"El contenido de la investigación se ha dividido en {len(content_chunks)} lotes para ser procesado.")

        final_structured_research = {
            "core_concepts": [], "technical_details": [], "use_cases": [],
            "expert_opinions": [], "competitor_comparison": [], "future_trends": []
        }

        for i, chunk in enumerate(content_chunks):
            logging.info(f"Procesando lote {i+1}/{len(content_chunks)} con el Curador Maestro...")
            chunk_research, raw_response_text = self.llm_fast.curate_and_structure_research(topic=topic, full_content_for_analysis=chunk)
            
            if not chunk_research:
                logging.warning(f"El Curador Maestro falló al procesar el lote {i+1}. Se continuará con el siguiente.")
                print("\n--- RESPUESTA EN BRUTO DEL LOTE FALLIDO ---")
                print(raw_response_text)
                print("--- FIN DE LA RESPUESTA ---")
                continue

            for key, value in chunk_research.items():
                if key in final_structured_research and isinstance(value, list):
                    final_structured_research[key].extend(value)
        
        if not final_structured_research or not any(final_structured_research.values()):
            logging.error("El Curador Maestro no pudo extraer y estructurar el contenido de ningún lote.")
            return False

        structured_research = final_structured_research
        self.workspace.save_structured_research(structured_research)
        
        # Lógica de aplanamiento de datos para compatibilidad con la bibliografía
        all_snippets = []
        if isinstance(structured_research, dict):
            for category_list in structured_research.values():
                if isinstance(category_list, list):
                    all_snippets.extend(category_list)

        self.state["research_catalog"] = [{"id": i + 1, "url": s.get('source', ''), "title": f"Fragmento #{i+1}", "content": s.get('snippet', '')} for i, s in enumerate(all_snippets)]
        self.state["youtube_transcript"] = youtube_transcript
        self.state["curated_sources"] = all_snippets

        self.workspace.save_progress(self.state)
        
        logging.info("Fase de investigación completada exitosamente.")
        return True