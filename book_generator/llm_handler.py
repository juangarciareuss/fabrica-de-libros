# book_generator/llm_handler.py

import google.generativeai as genai
import logging
import time
import os
import hashlib
import json
import config
# <<< CAMBIO: Se actualizan las importaciones de prompts >>>
from prompts import writing_agents, research_agents, structuring_agents, critic_agents, refactor_agents

CACHE_DIR = "cache"

def get_cache_filename(text_input):
    """Genera un nombre de archivo de caché basado en el hash del input."""
    return os.path.join(CACHE_DIR, f"{hashlib.md5(text_input.encode()).hexdigest()}.json")

def parse_json_from_response(text):
    """Extrae un objeto JSON del texto de respuesta de un LLM."""
    try:
        start_brace = text.find('{')
        start_bracket = text.find('[')
        if start_brace == -1 and start_bracket == -1: return None
        start = min(s for s in [start_brace, start_bracket] if s != -1)
        end_brace = text.rfind('}')
        end_bracket = text.rfind(']')
        end = max(end_brace, end_bracket)
        if start == -1 or end == -1: return None
        json_str = text[start:end+1]
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        return None

class LLMHandler:
    def __init__(self, api_key, model_name, performance_logger, agent_manifest):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name, safety_settings={'HARASSMENT': 'BLOCK_NONE'})
        self.token_usage = {"total": 0}
        self.performance_logger = performance_logger
        self.agent_manifest = agent_manifest
        logging.info(f"Modelo {model_name} inicializado.")

    def _call_gemini_with_retry(self, prompt, is_json_output=False, max_retries=3):
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_file = get_cache_filename(prompt)
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                self.token_usage['total'] += cached_data.get('usage', {}).get('total_token_count', 0)
                logging.info(f"✔️  Cargado de caché. Uso total acumulado: {self.token_usage['total']:,} tokens.")
                return cached_data.get('response'), cached_data.get('raw_text')
        
        logging.info("📞 Llamando a la API...")
        for attempt in range(max_retries):
            try:
                ## <<< CAMBIO: Se crea una configuración de generación más robusta >>>
                generation_config = genai.types.GenerationConfig(
                    # Forzamos la salida JSON si es necesario
                    response_mime_type="application/json" if is_json_output else None,
                    # Aumentamos el límite de tokens para respuestas largas y complejas
                    max_output_tokens=8192
                )

                ## <<< CAMBIO: Se pasa la nueva configuración a la llamada >>>
                response = self.model.generate_content(prompt, generation_config=generation_config)
                
                usage_metadata = response.usage_metadata
                self.token_usage['total'] += usage_metadata.total_token_count
                
                response_text = response.text
                parsed_response = parse_json_from_response(response_text) if is_json_output else response_text

                if is_json_output and parsed_response is None:
                    logging.warning("El parseo de JSON falló. La respuesta de la IA podría no ser un JSON válido.")

                with open(cache_file, 'w', encoding='utf-8') as f:
                    cache_data = {
                        'response': parsed_response,
                        'raw_text': response_text,
                        'usage': {'total_token_count': usage_metadata.total_token_count}
                    }
                    json.dump(cache_data, f, indent=4, ensure_ascii=False)
                
                logging.info(f"✅ Respuesta recibida. Uso total: {self.token_usage['total']:,} tokens.")
                return parsed_response, response_text

            except Exception as e:
                logging.error(f"Error en la llamada a la API (intento {attempt + 1}/{max_retries}): {e}")
                time.sleep(5)
        
        logging.critical("No se pudo obtener respuesta de la API.")
        return None, None


    def get_token_usage(self):
        return self.token_usage

# book_generator/llm_handler.py

    def _execute_agent_call(self, agent_id, prompt_template, is_json_output=False, **kwargs):
        """
        Método genérico para ejecutar cualquier agente y registrar su rendimiento.
        """
        agent_info = self.agent_manifest.get(agent_id, {})
        agent_role = agent_info.get('role', agent_id)
        logging.info(f"   -> [Activando] {agent_role}...")

        # --- VVVV LÓGICA DE TRADUCCIÓN DE CONTEXTO CORREGIDA Y MEJORADA VVVV ---
        
        # Para los escritores especialistas que envían 'context'
        if 'context' in kwargs:
            # Renombramos la clave a 'contextual_summary' que es la que esperan los prompts
            kwargs['contextual_summary'] = json.dumps(kwargs.pop('context'), indent=2, ensure_ascii=False)
        
        # Para agentes más antiguos o genéricos que puedan usar 'master_context'
        elif 'master_context' in kwargs:
            # También lo renombramos a 'contextual_summary'
            kwargs['contextual_summary'] = json.dumps(kwargs.pop('master_context'), indent=2, ensure_ascii=False)
        
        # Para el agente de resumen que ya usa 'contextual_summary' pero necesita ser string
        elif 'contextual_summary' in kwargs and not isinstance(kwargs['contextual_summary'], str):
            kwargs['contextual_summary'] = json.dumps(kwargs['contextual_summary'], indent=2, ensure_ascii=False)
        
        # --- ^^^^ FIN DE LA LÓGICA CORREGIDA ^^^^ ---

        if 'topics_to_avoid' in kwargs:
            topics = kwargs['topics_to_avoid']
            kwargs['forbidden_topics_clause'] = writing_agents.FORBIDDEN_TOPICS_CLAUSE.format(topics_to_avoid=topics) if topics else ""

        prompt = prompt_template.format(**kwargs)
        
        start_time = time.time()
        tokens_before = self.token_usage['total']
        parsed_response, raw_text = self._call_gemini_with_retry(prompt, is_json_output)
        
        duration = time.time() - start_time
        tokens_used = self.token_usage['total'] - tokens_before
        
        if self.performance_logger:
            self.performance_logger.log(
                agent_id=agent_id,
                event_type="execution",
                details={"success": parsed_response is not None, "duration_seconds": round(duration, 2), "tokens_used": tokens_used}
            )
            
        return parsed_response, raw_text

  # --- AGENTES (Llamadas consistentes al "motor" con su ID) ---

    def generate_web_queries(self, **kwargs):
        return self._execute_agent_call("research_web_query_generator", research_agents.WEB_QUERY_GENERATOR_PROMPT, True, **kwargs)

    def preselect_urls(self, **kwargs):
        # Este agente necesita un pre-procesamiento especial, por ahora lo dejamos fuera del motor
        logging.info("[AGENTE] 🔎 Pre-Selector de Fuentes...")
        formatted_list = "\n".join([f"- URL: {item['url']}\n  Título: {item['title']}" for item in kwargs.get('found_links_with_titles', [])])
        kwargs['formatted_urls_with_titles'] = formatted_list
        prompt = research_agents.URL_PRESELECTION_AGENT_PROMPT.format(**kwargs)
        return self._call_gemini_with_retry(prompt, is_json_output=True)

    def curate_and_structure_research(self, **kwargs):
        return self._execute_agent_call("research_master_curator", research_agents.MASTER_CURATOR_PROMPT, True, **kwargs)

    def generate_table_of_contents(self, **kwargs):
        return self._execute_agent_call("structuring_toc_generator", structuring_agents.TOC_GENERATION_PROMPT, True, **kwargs)

    def get_contextual_summary(self, **kwargs):
        return self._execute_agent_call("structuring_context_summarizer", structuring_agents.CONTEXTUAL_SUMMARY_PROMPT, False, **kwargs)

    def write_introduction(self, **kwargs):
        return self._execute_agent_call("writer_introduction", writing_agents.INTRODUCTION_WRITING_PROMPT, False, **kwargs)

    def write_conclusion(self, **kwargs):
        return self._execute_agent_call("writer_conclusion", writing_agents.CONCLUSION_WRITING_PROMPT, False, **kwargs)

    def write_foundational_chapter(self, **kwargs):
        return self._execute_agent_call("writer_foundational", writing_agents.FOUNDATIONAL_CHAPTER_PROMPT, False, **kwargs)

    def write_practical_tutorial_chapter(self, **kwargs):
        return self._execute_agent_call("writer_tutorial", writing_agents.PRACTICAL_TUTORIAL_PROMPT, False, **kwargs)

    def write_use_cases_chapter(self, **kwargs):
        return self._execute_agent_call("writer_use_cases", writing_agents.USE_CASES_CHAPTER_PROMPT, False, **kwargs)
    
    def write_comparison_chapter(self, **kwargs):
        return self._execute_agent_call("writer_comparison", writing_agents.COMPARISON_CHAPTER_PROMPT, False, **kwargs)
    
    def rewrite_paragraph_with_new_context(self, **kwargs):
        return self._execute_agent_call("writer_dynamic_rewriter", writing_agents.REWRITE_PARAGRAPH_PROMPT, False, **kwargs)

    def write_chapter(self, **kwargs): # Fallback
        return self._execute_agent_call("writer_generic_fallback", writing_agents.CHAPTER_WRITING_PROMPT, False, **kwargs)

    # --- Comité Editorial ---
    def critique_chapter(self, **kwargs):
        return self._execute_agent_call("critic_generic_fallback", critic_agents.CRITIQUE_CHAPTER_PROMPT, True, **kwargs)

    def critique_tutorial_chapter(self, **kwargs):
        return self._execute_agent_call("critic_tutorial", critic_agents.CRITIQUE_TUTORIAL_PROMPT, True, **kwargs)
    
    def critique_foundational_chapter(self, **kwargs):
        return self._execute_agent_call("critic_foundational", critic_agents.CRITIQUE_FOUNDATIONAL_PROMPT, True, **kwargs)

    def critique_use_cases_chapter(self, **kwargs):
        return self._execute_agent_call("critic_use_cases", critic_agents.CRITIQUE_USE_CASES_PROMPT, True, **kwargs)

    def refactor_chapter(self, **kwargs):
        return self._execute_agent_call("refactor_generic_fallback", refactor_agents.REFACTOR_CHAPTER_PROMPT, True, **kwargs)

    def refactor_tutorial_chapter(self, **kwargs):
        return self._execute_agent_call("refactor_tutorial", refactor_agents.REFACTOR_TUTORIAL_PROMPT, True, **kwargs)
        
    def refactor_foundational_chapter(self, **kwargs):
        return self._execute_agent_call("refactor_foundational", refactor_agents.REFACTOR_FOUNDATIONAL_PROMPT, True, **kwargs)
        
    def refactor_use_cases_chapter(self, **kwargs):
        return self._execute_agent_call("refactor_use_cases", refactor_agents.REFACTOR_USE_CASES_PROMPT, True, **kwargs)