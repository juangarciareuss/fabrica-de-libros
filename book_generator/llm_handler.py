import google.generativeai as genai
import logging
import time
import os
import hashlib
import json
import config
from prompts import writing_agents, research_agents, structuring_agents, quality_agents

# La importación relativa ahora apunta correctamente a otro módulo del paquete
from .researcher import perform_research_plan

CACHE_DIR = "cache"

# (Las funciones de caché y parseo de JSON no cambian)
def get_cache_filename(text_input):
    """Genera un nombre de archivo de caché basado en el hash de una entrada de texto."""
    return os.path.join(CACHE_DIR, f"{hashlib.md5(text_input.encode()).hexdigest()}.json")

def parse_json_from_response(text):
    """Intenta extraer y parsear un bloque de JSON de una respuesta de texto de forma robusta."""
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
    def __init__(self, api_key, model_name):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name, safety_settings={'HARASSMENT':'BLOCK_NONE'})
        self.token_usage = {"prompt": 0, "candidates": 0, "total": 0}
        logging.info(f"Modelo {model_name} inicializado.")

    def _call_gemini_with_retry(self, prompt, is_json_output=False, max_retries=3):
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_file = get_cache_filename(prompt)
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                self.token_usage['total'] += cached_data.get('usage', {}).get('total_token_count', 0)
                logging.info(f"✔️ Cargado de caché. Uso total acumulado: {self.token_usage['total']:,} tokens.")
                return cached_data['response']

        logging.info("📞 Llamando a la API...")
        for attempt in range(max_retries):
            try:
                config_gen = genai.types.GenerationConfig(response_mime_type="application/json") if is_json_output else None
                response = self.model.generate_content(prompt, generation_config=config_gen)
                
                usage_metadata = response.usage_metadata
                self.token_usage['total'] += usage_metadata.total_token_count
                
                response_text = response.text
                with open(cache_file, 'w', encoding='utf-8') as f:
                    cache_data = {
                        'response': parse_json_from_response(response_text) if is_json_output else response_text,
                        'usage': {'total_token_count': usage_metadata.total_token_count}
                    }
                    json.dump(cache_data, f, indent=4)

                logging.info(f"✅ Respuesta recibida. Uso total: {self.token_usage['total']:,} tokens.")
                return cache_data['response']
            except Exception as e:
                logging.error(f"Error en la llamada a la API (intento {attempt + 1}/{max_retries}): {e}")
                time.sleep(5)
        
        logging.critical("No se pudo obtener respuesta de la API.")
        return None

    def get_token_usage(self):
        return self.token_usage
    
    # --- AGENTES ---

    def verify_topic_reality(self, core_topic_term):
        logging.info("[AGENTE] 🕵️ Verificador de Realidad...")
        queries = [f'"{core_topic_term}"', f'"{core_topic_term}" Google AI', f'"{core_topic_term}" image generator review', f'Gemini "{core_topic_term}"']
        return perform_research_plan(queries, time_sensitive=True)

    def plan_research(self, topic, book_description, research_type='deep_context'):
        """
        Llama al Agente Director de Investigación, ahora especificando el tipo de investigación.
        """
        logging.info(f"[AGENTE] 🧠 Director de Investigación (Modo: {research_type})...")
        prompt = research_agents.RESEARCH_PLANNER_PROMPT.format(
            topic=topic, 
            book_description=book_description,
            research_type=research_type # <-- PARÁMETRO AÑADIDO
        )
        return self._call_gemini_with_retry(prompt, is_json_output=True)

    def evaluate_sources(self, topic, book_description, candidate_sources):
        logging.info(f"[AGENTE] 🧐 Analista de Inteligencia...")
        formatted = "\n".join([f"- Título: {s.get('title')}\n- URL: {s.get('link')}" for s in candidate_sources])
        prompt = research_agents.SOURCE_EVALUATION_PROMPT.format(topic=topic, book_description=book_description, source_count=len(candidate_sources), formatted_sources=formatted)
        return self._call_gemini_with_retry(prompt, is_json_output=True)

    def generate_table_of_contents(self, topic, book_description):
        logging.info("[AGENTE] 🏗️ Arquitecto de Contenidos...")
        prompt = structuring_agents.TOC_GENERATION_PROMPT.format(topic=topic, book_description=book_description)
        return self._call_gemini_with_retry(prompt, is_json_output=True)

    def get_contextual_summary(self, book_topic, chapter_title, chapter_focus, chapter_type, master_context):
        logging.info(f"  -> [SUMARIZADOR] Destilando contexto para '{chapter_title}'...")
        prompt = structuring_agents.CONTEXTUAL_SUMMARY_PROMPT.format(book_topic=book_topic, chapter_title=chapter_title, chapter_focus=chapter_focus, chapter_type=chapter_type, master_context=master_context)
        return self._call_gemini_with_retry(prompt)
    
    def write_introduction(self, book_topic, book_description, contextual_summary):
        prompt = writing_agents.INTRODUCTION_WRITING_PROMPT.format(book_topic=book_topic, book_description=book_description, contextual_summary=contextual_summary)
        return self._call_gemini_with_retry(prompt)

    def write_chapter(self, book_topic, book_description, chapter_title, chapter_type, chapter_focus, contextual_summary):
        prompt = writing_agents.CHAPTER_WRITING_PROMPT.format(book_topic=book_topic, book_description=book_description, chapter_title=chapter_title, chapter_type=chapter_type, chapter_focus=chapter_focus, contextual_summary=contextual_summary)
        return self._call_gemini_with_retry(prompt)
    
    def write_extended_use_cases(self, book_topic, book_description, chapter_title, chapter_focus, contextual_summary):
        logging.info(f"  -> [ESPECIALISTA] Generando capítulo de 20 casos de uso...")
        prompt = writing_agents.EXTENDED_USE_CASES_WRITING_PROMPT.format(book_topic=book_topic, book_description=book_description, chapter_title=chapter_title, chapter_focus=chapter_focus, contextual_summary=contextual_summary)
        return self._call_gemini_with_retry(prompt)

    def write_conclusion(self, book_topic, book_description, contextual_summary):
        prompt = writing_agents.CONCLUSION_WRITING_PROMPT.format(book_topic=book_topic, book_description=book_description, contextual_summary=contextual_summary)
        return self._call_gemini_with_retry(prompt)

    def critique_book(self, book_topic, book_description, book_content):
        logging.info("[AGENTE] 🕵️‍♂️ Crítico de Calidad...")
        text = "\n\n---\n\n".join([f"## {c['title']}\n\n{c['content']}" for c in book_content])
        prompt = quality_agents.CRITIQUE_PROMPT.format(book_topic=book_topic, book_description=book_description, full_book_text=text)
        return self._call_gemini_with_retry(prompt, is_json_output=True)

    def refactor_chapter(self, chapter_title, original_content, critique_feedback, contextual_summary):
        logging.info(f"  -> [REFACTORIZADOR] Reescribiendo '{chapter_title}'...")
        prompt = quality_agents.REFACTOR_CHAPTER_PROMPT.format(chapter_title=chapter_title, original_content=original_content, critique_feedback=critique_feedback, contextual_summary=contextual_summary)
        return self._call_gemini_with_retry(prompt)

