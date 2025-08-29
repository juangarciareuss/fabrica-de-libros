import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# Asegúrate de que tu ID del motor de búsqueda también esté aquí
SEARCH_ENGINE_ID = "759401a67fd4b471d" # Tu ID que ya habías confirmado

MODEL_NAME = "gemini-1.5-pro-latest"

# --- PLANTILLAS DE PROMPTS PARA LA FÁBRICA DE LIBROS ---

# 1. Prompt para el "Editor Jefe" (Evalúa las fuentes encontradas)
SOURCE_EVALUATION_PROMPT = """
PERSONA: Actúa como un exigente editor jefe de una revista de tecnología de prestigio como The Verge o Wired.

TAREA: Te he proporcionado una lista de {source_count} artículos encontrados en la web sobre el tema "{topic}". Tu misión es analizar esta lista y seleccionar las 3 a 5 fuentes de MAYOR CALIDAD que servirán como base para escribir una guía de inicio rápido ("...en 1 Hora").

LISTA DE FUENTES CANDIDATAS:
{formatted_sources}

CRITERIOS DE SELECCIÓN (en orden de importancia):
1.  **Fuentes Oficiales:** Prioriza al máximo los comunicados de prensa, blogs oficiales de la compañía o páginas del producto.
2.  **Análisis de Expertos:** Valora muy alto las reviews prácticas y los análisis profundos de medios tecnológicos reconocidos.
3.  **Contenido Sustancial:** Prefiere resúmenes que prometan contenido detallado sobre las características y el "cómo se usa".
4.  **Descarte:** Ignora fuentes que parezcan puro marketing, foros de baja calidad o noticias muy breves sin análisis.

FORMATO DE SALIDA:
Responde **únicamente con un objeto JSON válido**. El JSON debe ser un array. Cada objeto en el array debe representar una fuente seleccionada y contener una única clave: "url" con el link de la fuente.
"""

# 2. Prompt para el "Arquitecto de Contenidos" (Crea el índice del libro)

# EN config.py

TOC_GENERATION_PROMPT = """
PERSONA: Actúa como un diseñador instruccional y autor técnico experto. Tu especialidad es crear guías de aprendizaje rápidas que sean claras, prácticas y directas.

TEMA DEL LIBRO: "Guía de {topic}"

TAREA: Diseña el índice de contenidos ideal para una guía práctica de 50-70 páginas. La estructura debe ser lógica y enfocada en el aprendizaje del usuario. El libro debe tener la siguiente estructura obligatoria:
1.  Una introducción que conecte con la necesidad del lector y presente el valor de la herramienta.
2.  Exactamente 4 capítulos principales de desarrollo.
3.  Un capítulo de Conclusión.

REGLAS PARA LOS TÍTULOS:
- Los títulos de los capítulos deben ser **directos, descriptivos y orientados a la acción**.
- Deben comunicar claramente el contenido y el beneficio para el lector.
- **Evita** los títulos poéticos, abstractos o demasiado comerciales (ej. "La Revolución Mágica").
- Prefiere títulos como "Configuración Inicial y Primeros Pasos" o "Técnicas Avanzadas de Edición".

FORMATO DE SALIDA:
- Responde **únicamente con un objeto JSON válido**.
- El JSON debe ser un array de objetos.
- Cada objeto debe tener dos claves: "title" y "focus".
"""

# 3. Prompt para el "Escritor Experto" (Redacta cada capítulo)
CHAPTER_WRITING_PROMPT = """
PERSONA: Actúa como un profesor experto y un excelente comunicador tecnológico, como Marques Brownlee (MKBHD) o Nate Gentile. Tu estilo es claro, didáctico y entusiasta. Haces que la tecnología compleja parezca fácil y accesible.

AUDIENCIA: El lector es un entusiasta de la tecnología o un profesional que quiere aprender a usar una nueva herramienta rápidamente. No tiene tiempo que perder.

TAREA: Escribe el contenido completo y detallado para el siguiente capítulo de una guía de inicio rápido. El capítulo debe ser práctico y fácil de entender.

**TEMA GENERAL DE LA GUÍA:** {book_topic}

**TÍTULO DEL CAPÍTULO ACTUAL:** {chapter_title}

**OBJETIVO DE APRENDIZAJE DE ESTE CAPÍTULO:**
{chapter_focus}

**CONTEXTO DE INVESTIGACIÓN DISPONIBLE (Usa esta información como base principal):**
---
{full_context}
---

**INSTRUCCIONES ADICIONALES:**
- Escribe aproximadamente 1,000 - 1,500 palabras.
- Ve al grano. Usa un lenguaje claro y evita la jerga innecesaria.
- Estructura el contenido con subtítulos y listas para facilitar la lectura.
- Basa todas tus afirmaciones en la información del contexto de investigación.
- Responde únicamente con el texto completo del capítulo, sin incluir el título de nuevo.
"""

# EN config.py

# 4. Prompt para el "Agente Refactorizador" (Mejora un capítulo existente)
REFACTOR_CHAPTER_PROMPT = """
PERSONA: Eres un editor y escritor senior. Se te ha entregado el borrador de un capítulo de un libro y una crítica específica de tu editor jefe. Tu tarea es reescribir el capítulo para incorporar el feedback a la perfección.

TAREA: Reescribe y expande el siguiente capítulo de un libro basándote en la crítica proporcionada.

**TÍTULO DEL CAPÍTULO:** {chapter_title}

**BORRADOR ORIGINAL DEL CAPÍTULO:**
---
{original_content}
---

**CRÍTICA Y ORDEN DE MEJORA DEL EDITOR (Debes solucionar esto):**
---
{critique_feedback}
---

**CONTEXTO DE INVESTIGACIÓN DISPONIBLE (Usa esta información para encontrar nuevos detalles y ejemplos):**
---
{full_context}
---

**INSTRUCCIONES PARA LA REESCRITURA:**
1.  Mantén las ideas y datos correctos del borrador original.
2.  Soluciona **directamente** el problema señalado en la crítica. Si pide más ejemplos, añádelos. Si pide más profundidad técnica, desarróllala.
3.  Expande el contenido para que el nuevo capítulo sea significativamente más largo y de mayor calidad.
4.  Asegúrate de que la nueva versión sea coherente, esté bien estructurada y no introduzca información falsa.
5.  Responde únicamente con el texto del capítulo reescrito.
"""