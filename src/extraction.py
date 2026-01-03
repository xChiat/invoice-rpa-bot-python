import logging
import pdfplumber
from PIL import Image
import pytesseract
from io import BytesIO
from typing import List, Dict, Optional

# Configura logging básico (usaremos el log file de .env más adelante)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuracion pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extrae texto de un PDF estructurado usando pdfplumber.
    Si el PDF es escaneado, retorna vacío para fallback a OCR.
    
    Args:
        pdf_path (str): Ruta al archivo PDF.
    
    Returns:
        str: Texto extraído de todas las páginas.
    """
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        if text.strip():  # Si hay texto, es estructurado
            logger.info(f"Texto extraído exitosamente de {pdf_path} (estructurado).")
            return text
        else:
            logger.info(f"PDF {pdf_path} parece escaneado; fallback a OCR.")
            return ""  # Vacío para indicar uso de OCR
    except Exception as e:
        logger.error(f"Error al extraer texto de {pdf_path}: {e}")
        raise

def ocr_from_pdf(pdf_path: str, lang: str = 'spa') -> str:
    """
    Aplica OCR a un PDF (convierte páginas a imágenes).
    Útil para facturas escaneadas.
    
    Args:
        pdf_path (str): Ruta al archivo PDF.
        lang (str): Idioma para OCR ('spa' para español/chileno).
    
    Returns:
        str: Texto extraído via OCR.
    """
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Convierte página a imagen
                page_image = page.to_image(resolution=300)  # Alta resolución para mejor OCR
                pil_image = page_image.original  # Accede a la imagen PIL
                
                # Aplica OCR
                page_text = pytesseract.image_to_string(pil_image, lang=lang)
                text += page_text + "\n"
        logger.info(f"OCR completado para {pdf_path}.")
        return text
    except Exception as e:
        logger.error(f"Error en OCR para {pdf_path}: {e}")
        raise

def extract_invoice_data(pdf_path: str) -> Dict[str, str]:
    """
    Función principal: Intenta extracción estructurada, fallback a OCR.
    Por ahora, retorna texto crudo como dict simple; después parseamos con IA.
    
    Args:
        pdf_path (str): Ruta al PDF de factura chilena.
    
    Returns:
        Dict[str, str]: {'text': texto_extraido, 'method': 'structured' o 'ocr'}
    """
    text = extract_text_from_pdf(pdf_path)
    method = 'structured'
    
    if not text:
        text = ocr_from_pdf(pdf_path)
        method = 'ocr'
    
    return {'text': text.strip(), 'method': method}

# Ejemplo de uso (para testing; quítalo en producción)
if __name__ == "__main__":
    # Prueba con un PDF de ejemplo (ajusta path)
    sample_pdf = "./data/input/factura_ejemplo.pdf"
    data = extract_invoice_data(sample_pdf)
    print("Texto extraído:", data['text'])
    print("Método:", data['method'])