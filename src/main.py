import os
import logging
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler 
from extraction import extract_invoice_data
from ai_extraction import parse_invoice_text
from validation import validate_invoice_data

# Configura logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
IVA_RATE = float(os.getenv("IVA_RATE", 0.19))
INPUT_FOLDER = os.getenv("INPUT_FOLDER", "./data/input/")

def process_invoice(pdf_path: str, previous_num: int = None) -> None:
    """
    Flujo principal: Extrae, parsea, valida una factura.
    """
    try:
        # Extracción
        extracted = extract_invoice_data(pdf_path, use_advanced_ocr=True)
        text = extracted['text']
        method = extracted['method']
        quality = extracted.get('quality', 0.0)
        logger.info(f"Extracción completada vía {method} para {pdf_path} (calidad: {quality:.2%})")
        
        
        print()
        print("----------------")
        print("Extracted Text:")
        print("----------------")
        print(text)
        print()
        
       
        # Parsing con AI
        parsed_data = parse_invoice_text(text)
        logger.info(f"Datos parseados: {parsed_data}")
        
        print()
        print("--------------")
        print("Parsed Data:")
        print("--------------")
        print(parsed_data)
        print()
        
        # Validación
        valid, errors = validate_invoice_data(parsed_data, previous_invoice_num=previous_num, iva_rate=IVA_RATE)
        if valid:
            logger.info("Factura válida. Procede a procesamiento (BD, reporte, email).")
        else:
            logger.error(f"Factura inválida: {errors}")
    
    except Exception as e:
        logger.error(f"Error procesando {pdf_path}: {e}")

def scan_and_process_folder() -> None:
    """
    Escanea carpeta input y procesa PDFs nuevos.
    """
    for file in os.listdir(INPUT_FOLDER):
        if file.endswith(".pdf"):
            pdf_path = os.path.join(INPUT_FOLDER, file)
            process_invoice(pdf_path)  

if __name__ == "__main__":
    # Ejecución manual para test
    sample_pdf = os.path.join(INPUT_FOLDER, "factura_2.pdf") 
    process_invoice(sample_pdf)