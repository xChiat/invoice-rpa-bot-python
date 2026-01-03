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
# TODO: Agrega más vars como DB_URL, EMAIL_SENDER, etc.

def process_invoice(pdf_path: str, previous_num: int = None) -> None:
    """
    Flujo principal: Extrae, parsea, valida una factura.
    """
    try:
        # Extracción
        extracted = extract_invoice_data(pdf_path)
        text = extracted['text']
        method = extracted['method']
        logger.info(f"Extracción completada vía {method} para {pdf_path}")
        
        # Parsing con AI
        parsed_data = parse_invoice_text(text)
        logger.info(f"Datos parseados: {parsed_data}")
        
        # Validación
        valid, errors = validate_invoice_data(parsed_data, previous_invoice_num=previous_num, iva_rate=IVA_RATE)
        if valid:
            logger.info("Factura válida. Procede a procesamiento (BD, reporte, email).")
            # TODO: Llama a processing.py, db.py, output.py aquí
            # Ej. save_to_db(parsed_data)
            # generate_report(parsed_data)
            # send_email("Factura procesada exitosamente")
        else:
            logger.error(f"Factura inválida: {errors}")
            # TODO: Manejo de errores (retry, alert)
    
    except Exception as e:
        logger.error(f"Error procesando {pdf_path}: {e}")

def scan_and_process_folder() -> None:
    """
    Escanea carpeta input y procesa PDFs nuevos.
    """
    for file in os.listdir(INPUT_FOLDER):
        if file.endswith(".pdf"):
            pdf_path = os.path.join(INPUT_FOLDER, file)
            # TODO: Chequea si ya procesado (via BD)
            process_invoice(pdf_path)  # Pasa previous_num de BD si existe
            # TODO: Mueve a processed folder después

if __name__ == "__main__":
    # Ejecución manual para test
    sample_pdf = os.path.join(INPUT_FOLDER, "factura_1.pdf") 
    process_invoice(sample_pdf)
    
    # Automatización con scheduler (ejecuta cada 60s)
    scheduler = BlockingScheduler()
    scheduler.add_job(scan_and_process_folder, 'interval', seconds=60)
    logger.info("Iniciando scheduler para procesamiento automático...")
    scheduler.start()