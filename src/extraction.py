import os
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import PyPDF2
from pathlib import Path


def is_scanned_pdf(pdf_path):
    """
    Detecta si un PDF es escaneado (sin texto extraíble, solo imágenes).
    
    Args:
        pdf_path (str): Ruta al archivo PDF
        
    Returns:
        bool: True si el PDF es escaneado, False si contiene texto
    """
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Revisar el primer texto de la primera página
            if len(reader.pages) > 0:
                page = reader.pages[0]
                text = page.extract_text()
                
                # Si no hay texto o es muy poco, considerar como escaneado
                if text is None or len(text.strip()) < 10:
                    return True
            return False
    except Exception as e:
        print(f"Error al detectar si el PDF es escaneado: {e}")
        return True  # Asumir que es escaneado en caso de error


def convert_pdf_to_images(input_pdf, output_dir):
    """
    Convierte un PDF a una serie de imágenes.

    Args:
        input_pdf (str): Ruta al archivo PDF de entrada.
        output_dir (str): Directorio para guardar las imágenes convertidas.
    """
    pages = convert_from_path(input_pdf)

    # Guardar cada página como archivo JPEG usando Pillow
    for i, page in enumerate(pages):
        image_path = os.path.join(output_dir, f"page_{i}.jpg")
        page.save(image_path, "JPEG")


def extract_text_from_image(image_path):
    """
    Extrae texto de una imagen usando OCR (Reconocimiento Óptico de Caracteres).

    Args:
        image_path (str): Ruta al archivo de imagen.

    Returns:
        str: Texto extraído de la imagen.
    """
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    return text


def create_or_empty_dir(directory):
    """
    Crea o vacía el directorio especificado.

    Args:
        directory (str): Ruta del directorio.
    """
    if os.path.exists(directory):
        # Vaciar el directorio si ya existe
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error al eliminar {file_path}: {e}")
    else:
        # Crear el directorio si no existe
        os.makedirs(directory)


def extract_text_from_scanned_pdf(pdf_path, temp_images_dir=None):
    """
    Extrae texto de un PDF escaneado usando OCR.

    Args:
        pdf_path (str): Ruta al archivo PDF escaneado.
        temp_images_dir (str, optional): Directorio temporal para guardar imágenes. 
                                        Si no se proporciona, se crea uno temporal.

    Returns:
        str: Texto extraído del PDF completo.
    """
    if temp_images_dir is None:
        temp_images_dir = "_temp_images"
    
    # Crear o vaciar el directorio temporal
    create_or_empty_dir(temp_images_dir)
    
    try:
        # Convertir PDF a imágenes
        print(f"Convirtiendo PDF a imágenes: {pdf_path}")
        convert_pdf_to_images(pdf_path, temp_images_dir)
        
        # Extraer texto de todas las imágenes
        all_text = []
        for filename in sorted(
            os.listdir(temp_images_dir), 
            key=lambda x: int(x.split("_")[1].split(".")[0])
        ):
            if filename.endswith(".jpg") or filename.endswith(".png"):
                image_path = os.path.join(temp_images_dir, filename)
                print(f"Extrayendo texto de: {filename}")
                text = extract_text_from_image(image_path)
                # Limpiar encoding
                text = text.encode("utf-8", "ignore").decode("utf-8")
                all_text.append(text)
        
        # Combinar todo el texto
        extracted_text = "\n\n".join(all_text)
        return extracted_text
        
    finally:
        # Limpiar directorio temporal
        if os.path.exists(temp_images_dir):
            try:
                for filename in os.listdir(temp_images_dir):
                    file_path = os.path.join(temp_images_dir, filename)
                    os.remove(file_path)
                os.rmdir(temp_images_dir)
            except Exception as e:
                print(f"Advertencia: No se pudo limpiar el directorio temporal: {e}")


def extract_text_from_pdf(pdf_path):
    """
    Extrae texto de un PDF (escaneado o nativo).
    Si es escaneado, usa OCR. Si es nativo, extrae el texto directamente.

    Args:
        pdf_path (str): Ruta al archivo PDF.

    Returns:
        str: Texto extraído del PDF.
    """
    print(f"Procesando PDF: {pdf_path}")
    
    # Verificar si es un PDF escaneado
    if is_scanned_pdf(pdf_path):
        print("PDF detectado como escaneado. Usando OCR...")
        return extract_text_from_scanned_pdf(pdf_path)
    else:
        print("PDF detectado como nativo. Extrayendo texto directamente...")
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = []
                
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text.append(f"--- Página {page_num + 1} ---\n{page_text}")
                
                return "\n\n".join(text)
        except Exception as e:
            print(f"Error al extraer texto del PDF nativo: {e}")
            # Intentar como escaneado si falla la extracción nativa
            return extract_text_from_scanned_pdf(pdf_path)
