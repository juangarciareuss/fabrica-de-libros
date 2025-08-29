import os
import shutil
import sys
import logging
import time
from datetime import datetime
import config
from modules.researcher import perform_research, get_text_from_url
from modules.llm_handler import LLMHandler
from modules.book_assembler import create_word_document, convert_to_epub

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clear_cache():
    if os.path.exists("cache"):
        shutil.rmtree("cache")
        print("🧹 Caché borrado. Se generará contenido nuevo.")

def main():
    print("---------------------------------------------------------")
    print("🤖 Fábrica de Libros v5.0 (Control de Calidad Integrado) 🤖")
    print("---------------------------------------------------------")
    
    if input("¿Deseas borrar el caché y generar todo de nuevo? (s/n): ").lower() == 's':
        clear_cache()
    
    if not config.API_KEY or "TU_API_KEY" in config.API_KEY:
        logging.critical("La API Key de Google no está configurada en .env")
        sys.exit(1)
        
    book_topic = input("Por favor, introduce el tema del libro: ")
    
    llm = LLMHandler(api_key=config.API_KEY, model_name=config.MODEL_NAME)

    # ETAPA 1: GENERACIÓN DE ÍNDICE
    logging.info("[1/4] 🧠 Creando un índice a medida con Gemini...")
    custom_toc = llm.generate_table_of_contents(book_topic)
    if not custom_toc:
        logging.critical("No se pudo generar la tabla de contenidos.")
        sys.exit(1)

    # ETAPA 2: GENERACIÓN DE CAPÍTULOS CON INVESTIGACIÓN DEDICADA
    logging.info("[2/4] ✍️ Iniciando redacción de capítulos con investigación dedicada...")
    book_content = []
    all_source_urls = set()
    master_context_list = [] # Guardaremos toda la investigación aquí
    
    total_chapters = len(custom_toc)
    for i, chapter_data in enumerate(custom_toc):
        chapter_title = chapter_data['title'].replace('\n', ' ').strip()
        chapter_focus = chapter_data['focus']
        print(f"\n--- Procesando Capítulo {i+1}/{total_chapters}: {chapter_title} ---")

        logging.info(f"   [A] Realizando investigación para: '{chapter_title}'")
        specific_query = f"{chapter_title} {chapter_focus} {book_topic}"
        candidate_sources = perform_research(specific_query, num_results=7)
        
        if not candidate_sources:
            logging.warning(f"No se encontraron fuentes candidatas para '{chapter_title}'.")
            chapter_context = "" # Contexto vacío si no se encuentra nada
        else:
            logging.info(f"   [B] IA evaluando fuentes para '{chapter_title}'...")
            selected_urls = llm.evaluate_sources(chapter_title, candidate_sources)
            all_source_urls.update(selected_urls)
            
            logging.info(f"   [C] Extrayendo contenido para '{chapter_title}'...")
            chapter_context_data = []
            for url in selected_urls:
                content = get_text_from_url(url)
                if content:
                    chapter_context_data.append({"url": url, "content": content})
                time.sleep(1)
            
            chapter_context = "\n\n---\n\n".join([f"Fuente: {d['url']}\n\n{d['content']}" for d in chapter_context_data])
            master_context_list.append(chapter_context)

        dynamic_prompt = config.CHAPTER_WRITING_PROMPT.format(book_topic=book_topic, chapter_title=chapter_title, chapter_focus=chapter_focus, full_context=chapter_context)
        content = llm.generate_chapter_content(chapter_title, book_topic, dynamic_prompt)
        if content:
            book_content.append({"title": chapter_title, "content": content, "level": 1})

    # --- ETAPA 3: CONTROL DE CALIDAD ASISTIDO POR IA ---
    logging.info("\n[3/4] 🧐 Lanzando Agente Crítico para el control de calidad...")
    full_book_text = "\n\n---\n\n".join([f"## {c['title']}\n\n{c['content']}" for c in book_content])
    critique_report = llm.critique_book(book_topic, full_book_text)
    master_context = "\n\n---\n\n".join(master_context_list)

    if critique_report:
        while True:
            print("\n\n--- INFORME DEL AGENTE CRÍTICO ---")
            for i, report in enumerate(critique_report):
                print(f"Capítulo {i+1}: {report['chapter_title']}")
                print(f"  Puntuación: {report['score']}/10")
                print(f"  A Mejorar: {report['improvement_needed']}")
            print("--------------------------------\n")
            action = input("¿Acción? [1] Aprobar y ensamblar, [2] Regenerar un capítulo, [s] Salir: ")
            if action == '1': break
            if action == 's': sys.exit("Proceso finalizado por el usuario.")
            if action == '2':
                try:
                    chapter_num_str = input("Introduce el número del capítulo a regenerar (ej. 2): ")
                    chapter_num_to_regen = int(chapter_num_str) - 1
                    if 0 <= chapter_num_to_regen < len(book_content):
                        chapter_to_regen = book_content[chapter_num_to_regen]
                        critique_for_chapter = critique_report[chapter_num_to_regen]['improvement_needed']
                        new_content = llm.refactor_chapter(chapter_to_regen['title'], chapter_to_regen['content'], critique_for_chapter, master_context, book_topic)
                        if new_content:
                            book_content[chapter_num_to_regen]['content'] = new_content
                            print(f"✅ Capítulo {chapter_num_str} regenerado y mejorado con éxito.")
                            full_book_text = "\n\n---\n\n".join([f"## {c['title']}\n\n{c['content']}" for c in book_content])
                            critique_report = llm.critique_book(book_topic, full_book_text)
                        else:
                            print(f"❌ No se pudo regenerar el capítulo {chapter_num_str}.")
                    else:
                        print("Número de capítulo inválido.")
                except (ValueError, IndexError):
                    print("Entrada inválida. Por favor, introduce un número válido de la lista.")
    else:
        logging.warning("El Agente Crítico no pudo generar un informe. Se procederá a ensamblar.")

    # ETAPA 4: ENSAMBLAJE FINAL
    logging.info("\n[4/4] 📚 Ensamblando y exportando los archivos finales...")
    safe_title = "".join(x for x in book_topic if x.isalnum() or x in " _-").strip().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d")
    final_book_title = f"{safe_title}_{timestamp}"
    book_content.append({"title": "Fuentes Consultadas", "content": "\n".join(sorted(list(all_source_urls))), "level": 1})
    docx_path = create_word_document(final_book_title, book_content)
    epub_path = convert_to_epub(docx_path, final_book_title)
    
    print("\n---------------------------------------------------------")
    print("🎉 ¡Proceso Completado Exitosamente! 🎉")
    print("---------------------------------------------------------")
    if docx_path: print(f"✔️ Documento Word guardado en: {docx_path}")
    if epub_path: print(f"✔️ Archivo EPUB (para KDP) guardado en: {epub_path}")

if __name__ == "__main__":
    main()