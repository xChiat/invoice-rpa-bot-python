import logging
import pdfplumber
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import cv2
import numpy as np
from io import BytesIO
from typing import List, Dict, Optional, Tuple
from skimage import morphology

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
    """Convierte PIL Image a OpenCV BGR."""
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

def cv2_to_pil(cv_image: np.ndarray) -> Image.Image:
    """Convierte OpenCV BGR a PIL Image."""
    return Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))

def estimate_ocr_quality(text: str) -> float:
    """
    Estima la calidad del texto OCR.
    Retorna score 0-1 basado en coherencia del contenido.
    
    Métricas:
    - Presencia de palabras españolas comunes en facturas
    - Ausencia de caracteres extraños excesivos
    - Longitud mínima de texto
    """
    if not text or len(text.strip()) < 50:
        return 0.0
    
    text_lower = text.lower()
    
    # Palabras clave de facturas que esperamos encontrar
    keywords = [
        'factura', 'rut', 'fecha', 'total', 'neto', 'iva', 'cliente', 'emisor',
        'domicilio', 'descripción', 'cantidad', 'precio', 'monto', 'pago'
    ]
    
    # Contar keywords encontradas
    keyword_count = sum(1 for kw in keywords if kw in text_lower)
    keyword_score = keyword_count / len(keywords)
    
    # Penalizar caracteres extraños excesivos
    strange_chars = len([c for c in text if ord(c) > 127 and c not in 'áéíóúñüÁÉÍÓÚÑÜ'])
    strange_ratio = min(1.0, strange_chars / max(len(text), 1) * 10)
    
    # Penalizar líneas con demasiadas secuencias de símbolos
    broken_lines = sum(1 for line in text.split('\n') 
                       if len([c for c in line if not c.isalnum()]) / max(len(line), 1) > 0.5)
    broken_ratio = min(1.0, broken_lines / max(len(text.split('\n')), 1))
    
    # Score final: keywords positivo, caracteres extraños y líneas rotas negativo
    quality = (keyword_score * 0.5) - (strange_ratio * 0.25) - (broken_ratio * 0.25)
    return max(0.0, min(1.0, quality))

def auto_rotate_image(cv_image: np.ndarray) -> np.ndarray:
    """
    Detecta y corrige automáticamente la rotación del documento.
    Usa contornos para detectar el ángulo de inclinación.
    """
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    
    # Detectar bordes
    edges = cv2.Canny(gray, 50, 150)
    
    # Dilatar para conectar puntos
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(edges, kernel, iterations=3)
    
    # Encontrar contornos
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) == 0:
        logger.warning("No se detectaron contornos para rotación automática.")
        return cv_image
    
    # Obtener el contorno más grande (probable documento)
    largest_contour = max(contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(largest_contour)
    angle = rect[2]
    
    # Ajustar ángulo
    if angle < -45:
        angle = angle + 90
    
    if abs(angle) > 2:  # Solo rotar si el ángulo es significativo
        logger.info(f"Rotación automática detectada: {angle:.2f}°")
        h, w = cv_image.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(cv_image, rotation_matrix, (w, h), 
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
        return rotated
    
    return cv_image

def detect_invoice_region(cv_image: np.ndarray) -> Tuple[np.ndarray, tuple]:
    """
    Detecta automáticamente la región de la factura y recorta.
    Retorna imagen recortada y coordenadas (x, y, w, h).
    """
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    
    # Binarizar
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    
    # Operaciones morfológicas para limpiar ruido
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Encontrar contornos
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) == 0:
        logger.warning("No se detectó región de factura; usando imagen completa.")
        return cv_image, (0, 0, cv_image.shape[1], cv_image.shape[0])
    
    # Obtener el contorno más grande
    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)
    
    # Agregar padding para no perder datos en bordes
    padding = 20
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(cv_image.shape[1] - x, w + 2 * padding)
    h = min(cv_image.shape[0] - y, h + 2 * padding)
    
    cropped = cv_image[y:y+h, x:x+w]
    logger.info(f"Región de factura detectada: ({x}, {y}, {w}, {h})")
    
    return cropped, (x, y, w, h)

def preprocess_image_advanced(cv_image: np.ndarray, aggressive: bool = False) -> np.ndarray:
    """
    Preprocesamiento avanzado con OpenCV.
    Balanceado para preservar calidad de texto OCR.
    
    Args:
        cv_image: Imagen OpenCV BGR
        aggressive: Si True, aplica más procesamiento (puede perder texto fino)
    """
    # 1. Rotación automática (solo si es significativa)
    cv_image = auto_rotate_image(cv_image)
    
    # 2. Detección y recorte de región
    cv_image, _ = detect_invoice_region(cv_image)
    
    # 3. Upscaling moderado (1.5x en lugar de 2x)
    scale_factor = 1.5 if not aggressive else 2.0
    height = int(cv_image.shape[0] * scale_factor)
    width = int(cv_image.shape[1] * scale_factor)
    cv_image = cv2.resize(cv_image, (width, height), interpolation=cv2.INTER_CUBIC)
    
    # 4. Convertir a escala de grises
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    
    # 5. CLAHE suave (preservar más detalles)
    if aggressive:
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    else:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(16, 16))  # Más suave
    gray = clahe.apply(gray)
    
    # 6. Denoising bilateral (parameters reducidos)
    if aggressive:
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    else:
        denoised = cv2.bilateralFilter(gray, 5, 50, 50)  # Menos agresivo
    
    # 7. Threshold - usar método de Otsu en lugar de adaptativo (más estable)
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 8. Morfología mínima para preservar texto pequeño
    if aggressive:
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        processed = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open, iterations=1)
        processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel_close, iterations=1)
    else:
        # Sin morfología para preservar texto fino
        processed = binary
    
    logger.info(f"Preprocesamiento avanzado completado ({'agresivo' if aggressive else 'conservador'}).")
    return processed

def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Wrapper para mantener compatibilidad. Usa el preprocesamiento con PIL.
    Para OCR de mejor calidad, preferir usar preprocess_image_advanced con OpenCV.
    """
    image = image.resize((int(image.width * 1.5), int(image.height * 1.5)))
    image = image.convert('L')
    image = image.filter(ImageFilter.MedianFilter(size=3))
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.5)
    image = image.filter(ImageFilter.SHARPEN)
    image = image.point(lambda x: 0 if x < 150 else 255, '1')
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

def ocr_from_pdf(pdf_path: str, lang: str = 'spa', use_advanced_preprocessing: bool = True) -> tuple:
    """
    Extrae texto con OCR, intentando preprocesamiento avanzado primero.
    Si falla o da baja calidad, hace fallback a método tradicional.
    
    Retorna tupla: (text, method, quality_score)
    """
    text = ""
    method = "ocr_basic"
    quality_score = 0.0
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_image = page.to_image(resolution=300).original
                
                if use_advanced_preprocessing:
                    try:
                        # Intentar preprocesamiento avanzado
                        cv_image = pil_to_cv2(page_image)
                        processed_cv = preprocess_image_advanced(cv_image, aggressive=False)
                        processed_image = cv2_to_pil(processed_cv)
                        page_text = pytesseract.image_to_string(processed_image, lang='spa', 
                                                               config='--oem 3 --psm 3 --dpi 300')
                        
                        # Evaluar calidad
                        quality = estimate_ocr_quality(page_text)
                        
                        if quality < 0.2:  # Si calidad es muy baja, fallback a PIL
                            logger.warning(f"Página {page_num}: Calidad baja ({quality:.2f}) con OpenCV. Fallback a PIL.")
                            processed_image = preprocess_image(page_image)
                            page_text = pytesseract.image_to_string(processed_image, lang='spa', 
                                                                   config='--oem 3 --psm 3 --dpi 300')
                            method = "ocr_basic"
                        else:
                            logger.info(f"Página {page_num}: Preprocesamiento avanzado OK (calidad: {quality:.2f})")
                            method = "ocr_advanced"
                        
                        quality_score = max(quality_score, quality)
                        
                    except Exception as e:
                        logger.warning(f"Página {page_num}: Error en OpenCV ({e}). Fallback a PIL.")
                        processed_image = preprocess_image(page_image)
                        page_text = pytesseract.image_to_string(processed_image, lang='spa', 
                                                               config='--oem 3 --psm 3 --dpi 300')
                        method = "ocr_basic"
                else:
                    # Usar directamente PIL
                    processed_image = preprocess_image(page_image)
                    page_text = pytesseract.image_to_string(processed_image, lang='spa', 
                                                           config='--oem 3 --psm 3 --dpi 300')
                    method = "ocr_basic"
                
                text += page_text + "\n"
        
        logger.info(f"OCR completado para {pdf_path}. Método: {method}, Calidad: {quality_score:.2f}")
        return text, method, quality_score
        
    except Exception as e:
        logger.error(f"Error en OCR para {pdf_path}: {e}")
        raise

def extract_invoice_data(pdf_path: str, use_advanced_ocr: bool = True) -> Dict[str, any]:
    """
    Extrae datos de una factura. Intenta primero extracción estructurada,
    luego fallback a OCR con fallback inteligente basado en calidad.
    
    Args:
        pdf_path: Ruta al PDF de la factura
        use_advanced_ocr: Si True, intenta preprocesamiento avanzado con fallback automático
    
    Returns:
        Dict con:
        - 'text': texto extraído
        - 'method': método usado ('structured', 'ocr_advanced', 'ocr_basic')
        - 'quality': score de calidad 0-1
    """
    text = extract_text_from_pdf(pdf_path)
    method = 'structured'
    quality = 1.0
    
    if not text:
        text, method, quality = ocr_from_pdf(pdf_path, use_advanced_preprocessing=use_advanced_ocr)
    
    return {'text': text.strip(), 'method': method, 'quality': quality}

if __name__ == "__main__":
    sample_pdf = "./data/input/factura_1.pdf"
    data = extract_invoice_data(sample_pdf)
    print("Texto extraído:", data['text'])
    print("Método:", data['method'])