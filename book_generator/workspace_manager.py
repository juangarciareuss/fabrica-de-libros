# book_generator/workspace_manager.py

import os
import json
import logging
from datetime import datetime
from .book_assembler import create_final_document, convert_to_epub

class WorkspaceManager:
    def __init__(self, core_topic, existing_path=None):
        self.safe_title = "".join(x for x in core_topic if x.isalnum() or x in " _-").strip().replace(" ", "_")
        
        if existing_path:
            self.workspace_dir = existing_path
            self.timestamp = os.path.basename(existing_path).replace(f"{self.safe_title}_", "")
        else:
            self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.workspace_dir = os.path.join("workspace", f"{self.safe_title}_{self.timestamp}")
            os.makedirs(self.workspace_dir, exist_ok=True)

    def save_structured_research(self, structured_data):
        """
        Guarda el diccionario de la investigación estructurada en structured_research.json.
        """
        try:
            filepath = os.path.join(self.workspace_dir, "structured_research.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, indent=4, ensure_ascii=False)
            logging.info(f"🧠 Investigación estructurada guardada en: '{filepath}'")
        except Exception as e:
            logging.error(f"No se pudo guardar la investigación estructurada: {e}")

    def load_structured_research(self):
        """
        Carga el archivo structured_research.json desde el directorio de trabajo actual.
        """
        try:
            filepath = os.path.join(self.workspace_dir, "structured_research.json")
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logging.info(f"🧠 Investigación estructurada cargada desde: '{filepath}'")
                return data
            return None
        except Exception as e:
            logging.error(f"No se pudo cargar la investigación estructurada: {e}")
            return None

    def save_chapter(self, index, title, content):
        try:
            safe_chapter_title = "".join(x for x in title if x.isalnum() or x in " _-").strip().replace(" ", "_")
            filepath = os.path.join(self.workspace_dir, f"{index:02d}_{safe_chapter_title}.md")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n{content}")
            logging.info(f" 💾 Progreso guardado en: '{filepath}'")
        except Exception as e:
            logging.error(f"No se pudo guardar el capítulo '{title}': {e}")

    def save_bibliography(self, curated_sources):
        try:
            filepath = os.path.join(self.workspace_dir, "bibliography.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(curated_sources, f, indent=4, ensure_ascii=False)
            logging.info(f" 📚 Bibliografía curada guardada en: '{filepath}'")
        except Exception as e:
            logging.error(f"No se pudo guardar la bibliografía: {e}")

    def save_progress(self, state):
        try:
            filepath = os.path.join(self.workspace_dir, "progress.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4, ensure_ascii=False)
            logging.info("💾 Progreso del libro guardado en 'progress.json'")
        except Exception as e:
            logging.error(f"No se pudo guardar el progreso del libro: {e}")

    @staticmethod
    def find_latest_workspace(book_title):
        if not os.path.exists("workspace"):
            return None
        safe_title = "".join(x for x in book_title if x.isalnum() or x in " _-").strip().replace(" ", "_")
        workspaces = [d for d in os.listdir("workspace") if d.startswith(safe_title)]
        if not workspaces:
            return None
        latest_workspace_name = sorted(workspaces)[-1]
        return os.path.join("workspace", latest_workspace_name)

    def load_progress(self):
        try:
            progress_file = os.path.join(self.workspace_dir, "progress.json")
            if os.path.exists(progress_file):
                with open(progress_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                logging.info(f"✅ Progreso cargado exitosamente desde '{progress_file}'")
                return state
            return None
        except Exception as e:
            logging.error(f"No se pudo cargar el archivo de progreso: {e}")
            return None

    def read_youtube_transcript(self, filepath="youtube.txt"):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            logging.info(f"✅ Transcripción de YouTube cargada desde '{filepath}'.")
            return content
        except FileNotFoundError:
            logging.warning(f"No se encontró el archivo de transcripción '{filepath}'. Se continuará sin él.")
            return ""

    def check_if_final_book_exists(self):
        """
        Comprueba si los archivos finales del libro (DOCX o EPUB) ya existen en el workspace.
        """
        docx_path = os.path.join(self.workspace_dir, f"{self.safe_title}_FINAL_LIMPIO.docx")
        epub_path = os.path.join(self.workspace_dir, f"{self.safe_title}.epub")
        return os.path.exists(docx_path) or os.path.exists(epub_path)

    def assemble_and_export(self, book_content, curated_sources):
        logging.info("\n--- [FASE FINAL] ENSAMBLAJE Y EXPORTACIÓN ---")
        
        # <<< CAMBIO: Se generan dos versiones del documento >>>
        # 1. Versión con referencias internas [CITA: X] para tu revisión
        create_final_document(
            book_title=self.safe_title, 
            book_content=book_content, 
            curated_sources=curated_sources, 
            output_folder=self.workspace_dir, 
            template_path="MiPlantilla.docx", 
            include_internal_citations=True
        )
        
        # 2. Versión limpia para el lector final
        final_doc_path = create_final_document(
            book_title=self.safe_title, 
            book_content=book_content, 
            curated_sources=curated_sources, 
            output_folder=self.workspace_dir, 
            template_path="MiPlantilla.docx", 
            include_internal_citations=False
        )
        
        # 3. Se convierte a EPUB la versión limpia
        epub_path = convert_to_epub(final_doc_path, self.safe_title, output_folder=self.workspace_dir)
        
        print(f"\n✅ ¡Proceso Completado! Documentos finales guardados en '{self.workspace_dir}'")
        # Puedes añadir prints más detallados si quieres