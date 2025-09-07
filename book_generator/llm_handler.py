# book_generator/llm_handler.py

import google.generativeai as genai
import logging
import time
import os
import hashlib
import json
import config
from prompts import manager_agents, designer_agents, writing_agents, research_agents, structuring_agents, critic_agents, refactor_agents, audit_agents

CACHE_DIR = "cache"

def get_cache_filename(text_input):
    return os.path.join(CACHE_DIR, f"{hashlib.md5(text_input.encode()).hexdigest()}.json")

def parse_json_from_response(text):
    try:
        start_brace = text.find('{')
        start_bracket = text.find('[')
        if start_brace == -1 and start_bracket == -1: return None
        start = min(s for s in [start_brace, start_bracket] if s != -1)
        end_delimiter = '}' if text[start] == '{' else ']'
        end = text.rfind(end_delimiter)
        if start == -1 or end == -1: return None
        json_str = text[start:end+1]
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        return None

class LLMHandler:
    def __init__(self, api_key, model_name, performance_logger, agent_manifest):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.token_usage = {"total": 0}
        self.performance_logger = performance_logger
        self.agent_manifest = agent_manifest
        self.agent_configs = {
            #Designer
            "cover_designer": {"prompt": designer_agents.COVER_DESIGNER_PROMPT, "json_output": True}, # <-- LÍNEA AÑADIDA
            "cover_designer_gemini": {"prompt": designer_agents.GEMINI_COVER_DESIGNER_PROMPT, "json_output": False},
            # Manager
            "commercial_manager_analyst": {"prompt": manager_agents.COMMERCIAL_MANAGER_PROMPT, "json_output": True}, # <-- LÍNEA AÑADIDA
            "research_web_query_generator": {"prompt": research_agents.WEB_QUERY_GENERATOR_PROMPT, "json_output": True},
            "research_master_curator": {"prompt": research_agents.MASTER_CURATOR_PROMPT, "json_output": True},
            "structuring_toc_generator": {"prompt": structuring_agents.TOC_GENERATION_PROMPT, "json_output": True},
            "structuring_context_summarizer": {"prompt": structuring_agents.CONTEXTUAL_SUMMARY_PROMPT, "json_output": False},
            "writer_introduction": {"prompt": writing_agents.INTRODUCTION_WRITING_PROMPT, "json_output": False},
            "writer_conclusion": {"prompt": writing_agents.CONCLUSION_WRITING_PROMPT, "json_output": False},
            "writer_foundational": {"prompt": writing_agents.FOUNDATIONAL_CHAPTER_PROMPT, "json_output": False},
            "writer_tutorial": {"prompt": writing_agents.PRACTICAL_TUTORIAL_PROMPT, "json_output": False},
            "writer_use_cases": {"prompt": writing_agents.USE_CASES_CHAPTER_PROMPT, "json_output": False},
            "writer_comparison": {"prompt": writing_agents.COMPARISON_CHAPTER_PROMPT, "json_output": False},
            "writer_generic_fallback": {"prompt": writing_agents.CHAPTER_WRITING_PROMPT, "json_output": False},
            "critic_generic_fallback": {"prompt": critic_agents.CRITIQUE_CHAPTER_PROMPT, "json_output": True},
            "critic_tutorial": {"prompt": critic_agents.CRITIQUE_TUTORIAL_PROMPT, "json_output": True},
            "critic_foundational": {"prompt": critic_agents.CRITIQUE_FOUNDATIONAL_PROMPT, "json_output": True},
            "critic_use_cases": {"prompt": critic_agents.CRITIQUE_USE_CASES_PROMPT, "json_output": True},
            "critic_comparison": {"prompt": critic_agents.CRITIQUE_COMPARISON_PROMPT, "json_output": True},
            "refactor_generic_fallback": {"prompt": refactor_agents.REFACTOR_CHAPTER_PROMPT, "json_output": True},
            "refactor_tutorial": {"prompt": refactor_agents.REFACTOR_TUTORIAL_PROMPT, "json_output": True},
            "refactor_foundational": {"prompt": refactor_agents.REFACTOR_FOUNDATIONAL_PROMPT, "json_output": True},
            "refactor_use_cases": {"prompt": refactor_agents.REFACTOR_USE_CASES_PROMPT, "json_output": True},
            "refactor_comparison": {"prompt": refactor_agents.REFACTOR_COMPARISON_PROMPT, "json_output": True},
            "content_auditor": {"prompt": audit_agents.CONTENT_AUDITOR_PROMPT, "json_output": True},
        }
        logging.info(f"Modelo {model_name} inicializado con {len(self.agent_configs)} agentes configurados.")

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
                generation_config = genai.types.GenerationConfig(
                    response_mime_type="application/json" if is_json_output else "text/plain",
                    max_output_tokens=8192
                )
                response = self.model.generate_content(prompt, generation_config=generation_config)
                usage_metadata = response.usage_metadata
                self.token_usage['total'] += usage_metadata.total_token_count
                response_text = response.text
                parsed_response = parse_json_from_response(response_text) if is_json_output else response_text
                if is_json_output and parsed_response is None:
                    logging.warning("El parseo de JSON falló. La respuesta de la IA podría no ser un JSON válido.")
                with open(cache_file, 'w', encoding='utf-8') as f:
                    cache_data = {'response': parsed_response, 'raw_text': response_text, 'usage': {'total_token_count': usage_metadata.total_token_count}}
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

    def _execute_agent_call(self, agent_id, prompt_template, is_json_output=False, **kwargs):
        agent_info = self.agent_manifest.get(agent_id, {})
        agent_role = agent_info.get('role', agent_id)
        logging.info(f"   -> [Activando] {agent_role}...")

        # --- !! LÓGICA CORREGIDA !! ---
        # Maneja la cláusula de temas prohibidos si es necesaria en el prompt.
        if '{forbidden_topics_clause}' in prompt_template:
            topics = kwargs.get('topics_to_avoid', [])
            if topics:
                # Usamos la plantilla original de la cláusula
                kwargs['forbidden_topics_clause'] = writing_agents.FORBIDDEN_TOPICS_CLAUSE.format(topics_to_avoid=topics)
            else:
                # Si no hay temas que evitar, se inserta una cadena vacía.
                kwargs['forbidden_topics_clause'] = ""
        # --- FIN DE LA CORRECCIÓN ---
        
        try:
            prompt = prompt_template.format(**kwargs)
        except KeyError as e:
            logging.critical(f"Error FATAL al formatear el prompt para el agente '{agent_id}'. Falta la clave: {e}")
            logging.error(f"Argumentos disponibles: {list(kwargs.keys())}")
            return None, f"Error de formato de prompt: Falta la clave {e}"

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

    def call_agent(self, agent_id, **kwargs):
        """
        Método genérico para llamar a cualquier agente configurado.
        """
        if agent_id not in self.agent_configs:
            logging.error(f"Agente con ID '{agent_id}' no encontrado en la configuración.")
            return None, None
        
        config = self.agent_configs[agent_id]
        prompt_template = config["prompt"]
        is_json_output = config["json_output"]
        
        return self._execute_agent_call(agent_id, prompt_template, is_json_output, **kwargs)