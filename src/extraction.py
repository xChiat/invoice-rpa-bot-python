import logging
import pdfplumber
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from io import BytesIO
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(image: Image.Image) -> Image.Image:
    image = image.resize((int(image.width * 1.5), int(image.height * 1.5)))  # Upscale para mejor res
    image = image.convert('L')  # Grayscale
    image = image.filter(ImageFilter.MedianFilter(size=3))  # Denoising
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.5)  # Aumenta contraste
    image = image.filter(ImageFilter.SHARPEN)
    image = image.point(lambda x: 0 if x < 150 else 255, '1')  # Threshold ajustado a 150 para facturas claras
    return image

def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        if text.strip():
            logger.info(f"Texto extraído exitosamente de {pdf_path} (estructurado).")
            return text
        else:
            logger.info(f"PDF {pdf_path} parece escaneado; fallback a OCR.")
            return ""  
    except Exception as e:
        logger.error(f"Error al extraer texto de {pdf_path}: {e}")
        raise

def ocr_from_pdf(pdf_path: str, lang: str = 'spa') -> str:
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_image = page.to_image(resolution=300).original  # Alta res
                processed_image = preprocess_image(page_image)
                page_text = pytesseract.image_to_string(processed_image, lang='spa', config='--oem 3 --psm 3 --dpi 300')
                text += page_text + "\n"
        logger.info(f"OCR completado para {pdf_path} con preprocesamiento.")
        return text
    except Exception as e:
        logger.error(f"Error en OCR para {pdf_path}: {e}")
        raise

def extract_invoice_data(pdf_path: str) -> Dict[str, str]:
    text = extract_text_from_pdf(pdf_path)
    method = 'structured'
    
    if not text:
        text = ocr_from_pdf(pdf_path)
        method = 'ocr'
    
    return {'text': text.strip(), 'method': method}

if __name__ == "__main__":
    sample_pdf = "./data/input/factura_1.pdf"
    data = extract_invoice_data(sample_pdf)
    print("Texto extraído:", data['text'])
    print("Método:", data['method'])