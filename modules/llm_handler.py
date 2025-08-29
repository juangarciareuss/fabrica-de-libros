import google.generativeai as genai
import logging
import time
import os
import hashlib
import json
import config

CACHE_DIR = "cache"

def get_cache_filename(text_input):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{hashlib.md5(text_input.encode()).hexdigest()}.txt")

class LLMHandler:
    def __init__(self, api_key, model_name):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        logging.info(f"Modelo {model_name} inicializado.")

    def _call_gemini_with_retry(self, prompt, max_retries=3):
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                logging.error(f"Error en la llamada a la API (intento {attempt + 1}): {e}")
                time.sleep(5)
        logging.critical("No se pudo obtener respuesta de la API después de varios intentos.")
        return None

    def evaluate_sources(self, topic, candidate_sources):
        logging.info(f"🤖 IA evaluando {len(candidate_sources)} fuentes candidatas...")
        formatted_sources = "\n".join([f"Fuente {i+1}:\n- Título: {source['title']}\n- URL: {source['link']}\n- Resumen: {source['snippet']}\n" for i, source in enumerate(candidate_sources)])
        prompt = config.SOURCE_EVALUATION_PROMPT.format(source_count=len(candidate_sources), topic=topic, formatted_sources=formatted_sources)
        response_text = self._call_gemini_with_retry(prompt)
        if not response_text: return []
        try:
            json_response = response_text.strip().replace("```json", "").replace("```", "")
            selected_urls = [item['url'] for item in json.loads(json_response)]
            logging.info(f"🤖 IA seleccionó {len(selected_urls)} fuentes de alta calidad.")
            return selected_urls
        except Exception as e:
            logging.error(f"Error al procesar la selección de fuentes de la IA: {e}")
            return []

    def generate_table_of_contents(self, book_topic): # Ya no necesita 'full_context'
        logging.info("🧠 Generando tabla de contenidos a medida...")
        prompt = config.TOC_GENERATION_PROMPT.format(topic=book_topic) # Prompt simplificado
        response_text = self._call_gemini_with_retry(prompt)
        if not response_text: return None
        try:
            json_response = response_text.strip().replace("```json", "").replace("```", "")
            toc = json.loads(json_response)
            logging.info(f"Tabla de contenidos generada con {len(toc)} capítulos.")
            return toc
        except Exception as e:
            logging.error(f"Error al decodificar la respuesta JSON de la tabla de contenidos: {e}")
            return None

    def generate_chapter_content(self, chapter_title, book_topic, full_prompt):
        logging.info(f"Procesando capítulo: '{chapter_title}'...")
        prompt_identifier = f"{book_topic}-{chapter_title}"
        cache_file = get_cache_filename(prompt_identifier)
        if os.path.exists(cache_file):
            logging.info(f"✔️ Encontrado en caché. Cargando desde archivo...")
            with open(cache_file, 'r', encoding='utf-8') as f:
                return f.read()
        logging.info("❌ No encontrado en caché. Generando con Gemini...")
        content = self._call_gemini_with_retry(full_prompt)
        if content:
            os.makedirs(CACHE_DIR, exist_ok=True)
            logging.info(f"Guardando nuevo contenido en caché...")
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logging.info(f"Contenido para '{chapter_title}' generado y guardado.")
        else:
            logging.error(f"Falló la generación de contenido para '{chapter_title}'.")
        return content
        
    def critique_book(self, book_topic, full_book_text):
        logging.info("🤖 Agente Crítico iniciando análisis de calidad del libro...")
        prompt = f"""
        **ACTÚA COMO UN AGENTE CRÍTICO DE LIBROS**
        **1. PERSONA:** Eres un lector exigente de guías tecnológicas. Buscas valor, profundidad y claridad. Si un libro es superficial o repetitivo, lo detectas al instante. Tu objetivo es proporcionar feedback accionable para transformar un borrador bueno en un producto de 5 estrellas.
        **2. MISIÓN:** Analiza el siguiente borrador del libro "{book_topic}". Evalúa su calidad general y la de cada capítulo. Sé duro pero constructivo.
        **3. TEXTO COMPLETO DEL BORRADOR:**
        ---
        {full_book_text}
        ---
        **4. INFORME REQUERIDO:** Genera un informe de crítica. Para cada capítulo, crea un objeto. El informe final debe ser una lista de estos objetos en formato JSON.
        REGLAS ESTRICTAS DEL JSON DE SALIDA:
        - Responde únicamente con un objeto JSON válido, sin texto introductorio.
        - El JSON debe ser un array donde cada objeto representa un capítulo.
        - Cada objeto debe tener 4 claves: "chapter_title", "score", "positive_feedback", "improvement_needed".
        """
        response_text = self._call_gemini_with_retry(prompt)
        if not response_text: return None
        try:
            json_response = response_text.strip().replace("```json", "").replace("```", "")
            critique = json.loads(json_response)
            return critique
        except Exception as e:
            logging.error(f"Error al procesar la crítica de la IA: {e}")
            return None

    # --- LA FUNCIÓN FINAL QUE FALTABA ---
    def refactor_chapter(self, chapter_title, original_content, critique_feedback, full_context, book_topic):
        """
        Reescribe un capítulo basándose en una crítica específica.
        """
        logging.info(f"🤖 Agente Refactorizador reescribiendo capítulo: '{chapter_title}'...")
        
        prompt = config.REFACTOR_CHAPTER_PROMPT.format(
            chapter_title=chapter_title,
            original_content=original_content,
            critique_feedback=critique_feedback,
            full_context=full_context
        )

        new_content = self._call_gemini_with_retry(prompt)

        if new_content:
            prompt_identifier = f"{book_topic}-{chapter_title}"
            cache_file = get_cache_filename(prompt_identifier)
            logging.info(f"Guardando versión mejorada en caché: {cache_file}")
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            logging.info("Capítulo refactorizado y guardado.")
        else:
            logging.error("Falló la refactorización del capítulo.")

        return new_content