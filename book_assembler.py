from docx import Document
import pypandoc
import logging
import os
import re # <-- LÍNEA AÑADIDA PARA CORREGIR EL ERROR

def create_word_document(book_title, book_content, curated_sources, output_folder="output", template_path="MiPlantilla.docx"):
    """
    Crea un documento de Word, procesando marcadores de cita
    y construyendo una sección de referencias numerada.
    """
    if not os.path.exists(output_folder): os.makedirs(output_folder)
    doc_path = os.path.join(output_folder, f"{book_title}.docx")

    try:
        document = Document(template_path)
    except Exception:
        document = Document()

    document.add_heading(book_title, level=0)
    
    cited_sources_map = {}
    citation_counter = 1

    # Procesamiento de Contenido con Citaciones
    # (La lógica de esta sección no cambia)
    introduction = next((c for i, c in enumerate(book_content) if c.get('type') == 'introduction'), book_content.pop(0) if book_content else None)
    conclusion = next((c for i, c in enumerate(book_content) if c.get('type') == 'conclusion'), book_content.pop(-1) if book_content else None)

    if introduction:
        _add_chapter_to_doc(document, introduction, curated_sources, cited_sources_map)

    dev_chapters = [c for c in book_content if c not in [introduction, conclusion]]
    for chapter in dev_chapters:
        _add_chapter_to_doc(document, chapter, curated_sources, cited_sources_map)
    
    if conclusion:
        _add_chapter_to_doc(document, conclusion, curated_sources, cited_sources_map)
    
    # Construcción de la Sección de Referencias
    document.add_heading("Referencias", level=1)
    if cited_sources_map:
        sorted_sources = sorted(cited_sources_map.items(), key=lambda item: item[1])
        for url, num in sorted_sources:
            p = document.add_paragraph()
            p.add_run(f"[{num}] ").bold = True
            p.add_run(url)
    else:
        document.add_paragraph("No se citaron fuentes externas.")

    document.save(doc_path)
    logging.info(f"Documento de Word con citaciones guardado en: {doc_path}")
    return doc_path

def _add_chapter_to_doc(document, chapter_data, curated_sources, cited_sources_map):
    """
    Función auxiliar para añadir un capítulo al documento,
    limpiando anotaciones y procesando citas visibles.
    """
    citation_counter = len(cited_sources_map) + 1
    document.add_heading(chapter_data.get('title', 'Sin Título'), level=1)
    
    content = chapter_data.get('content', '')
    if content:
        # Limpieza de anotaciones invisibles
        content = re.sub(r'<!-- CITE:.*?-->', '', content)

        for para_text in content.split('\n'):
            if para_text.strip().startswith('### '):
                document.add_heading(para_text.strip().replace('### ', ''), level=2)
            elif para_text.strip():
                p = document.add_paragraph()
                
                # Lógica para encontrar y reemplazar citas visibles [fuente: N]
                parts = re.split(r'(\[fuente:\s*[\d,\s]+\])', para_text)
                for part in parts:
                    match = re.match(r'\[fuente:\s*([\d,\s]+)\]', part)
                    if match:
                        source_ids = [int(s.strip()) for s in match.group(1).split(',')]
                        for source_id in source_ids:
                            source = next((s for s in curated_sources if s.get('id') == source_id), None)
                            if source:
                                url = source['url']
                                if url not in cited_sources_map:
                                    cited_sources_map[url] = citation_counter
                                    citation_counter += 1
                                citation_num = cited_sources_map[url]
                                run = p.add_run(f"[{citation_num}]")
                                run.font.superscript = True
                    else:
                        # Añade texto normal y maneja negritas
                        sub_parts = part.split('**')
                        for i, sub_part in enumerate(sub_parts):
                            run = p.add_run(sub_part)
                            if i % 2 == 1:
                                run.bold = True
    document.add_page_break()


def convert_to_epub(docx_path, book_title, output_folder="output"):
    # (Esta función no cambia)
    if not docx_path: return None
    epub_path = os.path.join(output_folder, f"{book_title}.epub")
    try:
        logging.info("Iniciando conversión a EPUB...")
        pypandoc.convert_file(docx_path, 'epub', outputfile=epub_path, extra_args=['--toc'])
        logging.info(f"Archivo EPUB guardado en: {epub_path}")
        return epub_path
    except Exception as e:
        logging.error(f"Error durante la conversión a EPUB: {e}")
        return None

