"""
Servicio de procesamiento de PDFs.
Detecta tipo de PDF y extrae texto usando extracción directa u OCR.
"""
import os
import tempfile
from pathlib import Path
from typing import Tuple
import logging

from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import PyPDF2

logger = logging.getLogger(__name__)


class PDFProcessorService:
    """
    Servicio para procesar PDFs y extraer texto.
    Detecta automáticamente si el PDF es escaneado o digital.
    """
    
    def __init__(self):
        """Inicializar servicio"""
        logger.info("PDFProcessorService initialized")
    
    def is_scanned_pdf(self, pdf_content: bytes) -> bool:
        """
        Detecta si un PDF es escaneado (sin texto extraíble, solo imágenes).
        
        Args:
            pdf_content: Contenido binario del PDF
            
        Returns:
            True si el PDF es escaneado, False si contiene texto
        """
        try:
            # Crear archivo temporal para leer con PyPDF2
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file.write(pdf_content)
                tmp_path = tmp_file.name
            
            try:
                with open(tmp_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    
                    # Revisar el texto de la primera página
                    if len(reader.pages) > 0:
                        page = reader.pages[0]
                        text = page.extract_text()
                        
                        # Si no hay texto o es muy poco, considerar como escaneado
                        if text is None or len(text.strip()) < 10:
                            logger.info("PDF detected as scanned (no extractable text)")
                            return True
                    
                    logger.info("PDF detected as digital (has extractable text)")
                    return False
            finally:
                # Limpiar archivo temporal
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
        except Exception as e:
            logger.error(f"Error detecting PDF type: {e}")
            return True  # Asumir escaneado en caso de error
    
    def _convert_pdf_to_images(self, pdf_path: str, output_dir: str) -> list:
        """
        Convierte un PDF a serie de imágenes.
        
        Args:
            pdf_path: Ruta al archivo PDF
            output_dir: Directorio para guardar imágenes
            
        Returns:
            Lista de paths de imágenes creadas
        """
        logger.info(f"Converting PDF to images: {pdf_path}")
        pages = convert_from_path(pdf_path)
        
        image_paths = []
        for i, page in enumerate(pages):
            image_path = os.path.join(output_dir, f"page_{i}.jpg")
            page.save(image_path, "JPEG")
            image_paths.append(image_path)
        
        logger.info(f"Created {len(image_paths)} images")
        return image_paths
    
    def _extract_text_from_image(self, image_path: str) -> str:
        """
        Extrae texto de una imagen usando OCR.
        
        Args:
            image_path: Ruta al archivo de imagen
            
        Returns:
            Texto extraído
        """
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang='spa')  # Español
        return text
    
    def _extract_text_from_scanned_pdf(self, pdf_content: bytes) -> str:
        """
        Extrae texto de un PDF escaneado usando OCR.
        
        Args:
            pdf_content: Contenido binario del PDF
            
        Returns:
            Texto extraído del PDF completo
        """
        # Crear directorio temporal
        with tempfile.TemporaryDirectory() as temp_dir:
            # Guardar PDF en temporal
            pdf_path = os.path.join(temp_dir, "input.pdf")
            with open(pdf_path, "wb") as f:
                f.write(pdf_content)
            
            # Convertir a imágenes
            images_dir = os.path.join(temp_dir, "images")
            os.makedirs(images_dir, exist_ok=True)
            
            image_paths = self._convert_pdf_to_images(pdf_path, images_dir)
            
            # Extraer texto de todas las imágenes
            logger.info(f"Extracting text from {len(image_paths)} images using OCR...")
            all_text = []
            
            for image_path in image_paths:
                logger.debug(f"Processing: {os.path.basename(image_path)}")
                text = self._extract_text_from_image(image_path)
                # Limpiar encoding
                text = text.encode("utf-8", "ignore").decode("utf-8")
                all_text.append(text)
            
            # Combinar todo el texto
            extracted_text = "\n\n".join(all_text)
            logger.info(f"OCR extraction completed. Extracted {len(extracted_text)} characters")
            
            return extracted_text
    
    def _extract_text_from_digital_pdf(self, pdf_content: bytes) -> str:
        """
        Extrae texto de un PDF digital (con texto extraíble).
        
        Args:
            pdf_content: Contenido binario del PDF
            
        Returns:
            Texto extraído del PDF
        """
        logger.info("Extracting text from digital PDF...")
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            tmp_path = tmp_file.name
        
        try:
            with open(tmp_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text_parts = []
                
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"--- Página {page_num + 1} ---\n{page_text}")
                
                extracted_text = "\n\n".join(text_parts)
                logger.info(f"Direct extraction completed. Extracted {len(extracted_text)} characters")
                
                return extracted_text
        finally:
            # Limpiar archivo temporal
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def extract_text(self, pdf_content: bytes) -> Tuple[str, int]:
        """
        Extrae texto de un PDF (escaneado o digital).
        
        Args:
            pdf_content: Contenido binario del PDF
            
        Returns:
            Tuple[str, int]: (texto_extraído, tipo_factura_id)
                tipo_factura_id: 1 = Escaneada (OCR), 2 = Digital
        """
        try:
            # Detectar tipo de PDF
            is_scanned = self.is_scanned_pdf(pdf_content)
            
            if is_scanned:
                tipo_factura_id = 1  # Escaneada
                text = self._extract_text_from_scanned_pdf(pdf_content)
            else:
                tipo_factura_id = 2  # Digital
                text = self._extract_text_from_digital_pdf(pdf_content)
            
            return text, tipo_factura_id
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}", exc_info=True)
            # Intentar con OCR como fallback
            try:
                logger.info("Attempting OCR fallback...")
                text = self._extract_text_from_scanned_pdf(pdf_content)
                return text, 1  # Escaneada
            except Exception as e2:
                logger.error(f"OCR fallback also failed: {e2}", exc_info=True)
                raise Exception(f"Failed to extract text from PDF: {str(e)}")


# Singleton instance
pdf_processor_service = PDFProcessorService()
