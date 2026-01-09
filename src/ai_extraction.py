import logging
import os
import re
from typing import Dict, Optional
from dotenv import load_dotenv
from transformers import pipeline, AutoTokenizer, AutoModelForQuestionAnswering
from datetime import datetime  # Para normalizar fechas

# Configura logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
if not HF_TOKEN:
    raise ValueError("HUGGINGFACE_TOKEN no encontrado en .env. Crea uno en huggingface.co/settings/tokens.")

# Carga el modelo QA para español (usa token para auth)
MODEL_NAME = "mrm8488/bert-base-spanish-wwm-cased-finetuned-spa-squad2-es"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
model = AutoModelForQuestionAnswering.from_pretrained(MODEL_NAME, token=HF_TOKEN)
qa_pipeline = pipeline("question-answering", model=model, tokenizer=tokenizer)

# Diccionario de meses en español para parsing textual
MESES_ESPANOL = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

def normalize_date(date_str: str) -> Optional[str]:
    """
    Normaliza fecha textual a 'DD-MM-YYYY'.
    Ej. '26 de julio de 2020' -> '26-07-2020'
    """
    date_str = date_str.lower().strip()
    match = re.match(r'(\d{1,2}) (de )?([a-z]+) (de )?(\d{4})', date_str)
    if match:
        day, _, month_name, _, year = match.groups()
        month = MESES_ESPANOL.get(month_name)
        if month:
            try:
                dt = datetime(int(year), month, int(day))
                return dt.strftime('%d-%m-%Y')
            except ValueError:
                pass
    return None

def extract_field_with_qa(text: str, question: str) -> Optional[str]:
    """
    Usa QA para extraer un campo preguntando al modelo.
    """
    try:
        result = qa_pipeline(question=question, context=text)
        answer = result['answer'].strip()
        if result['score'] > 0.3: 
            return answer
        else:
            logger.warning(f"Confianza baja ({result['score']}) para '{question}'.")
            return None
    except Exception as e:
        logger.error(f"Error en QA para '{question}': {e}")
        return None

def regex_fallback(text: str, pattern: str, flags: int = re.IGNORECASE) -> Optional[str]:
    """
    Fallback con regex, ahora soporta flags personalizados.
    """
    match = re.search(pattern, text, flags=flags)
    return match.group(1).strip() if match else None

def parse_invoice_text(text: str) -> Dict[str, any]:
    fields = {}
    
    # 1. Número factura (tolerar N*, Nº, espacios)
    question = "¿Cuál es el número o Nº de la factura?"
    fields['numero_factura'] = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:Factura|Nº|N\*|Número|Serie)\s*[:\s]*(\d+)')
    
    # 2. Fecha (ya maneja textual, pero agrega variaciones)
    question = "¿Cuál es la fecha de emisión?"
    fecha_raw = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:Fecha|Emisión)\s*[:\s]*(\d{1,2} (de )?[a-zA-Z]+ (de |del )?\d{4})')
    fields['fecha_emision'] = normalize_date(fecha_raw) if fecha_raw else None
    
    # 3. Nombre emisor
    question = "¿Cuál es el nombre o denominación del emisor o empresa emisora?"
    fields['nombre_emisor'] = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:Emisor|De|Nombre emisor|SEÑOR\(ES\))\s*[:\s]*(.+?)(?=RUT|Domicilio|Giro)')
    
    # 4. Nombre destinatario
    question = "¿Cuál es el nombre o denominación del destinatario o cliente?"
    fields['nombre_destinatario'] = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:Destinatario|Para|SEÑOR\(ES\)|Nombre cliente)\s*[:\s]*(.+?)(?=RUT|Domicilio)')
    
    # 5. RUT emisor (tolerar espacios en RUT)
    question = "¿Cuál es el RUT del emisor?"
    rut_raw = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:RUT|Rut emisor)\s*[:\s]*(\d{1,2}\.?\d{3}\.?\d{3}-?[\dKk ])')
    fields['rut_emisor'] = rut_raw.strip() if rut_raw else None  # Limpia espacios finales
    
    # 6. Domicilio emisor
    question = "¿Cuál es el domicilio o dirección del emisor?"
    fields['domicilio_emisor'] = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:Domicilio emisor|Dirección emisor|DOMICILIO|LAUTARO)\s*[:\s]*(.+?)(?=Destinatario|Factura|COMUNA)')
    
    # 7. Domicilio destinatario
    question = "¿Cuál es el domicilio o dirección del destinatario?"
    fields['domicilio_destinatario'] = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:Domicilio destinatario|Dirección|GRAN BRETANA)\s*[:\s]*(.+?)(?=COMUNA|CIUDAD|Descrip)')
    
    # 8. Descripción (captura bloques largos)
    question = "¿Cuál es la descripción de las operaciones o detalle?"
    fields['descripcion_operaciones'] = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:Descrip|Operaciones|Detalle|Estado de Pago)\s*[:\s]*(.+?)(?=Referencias|Neto|Monto)', flags=re.IGNORECASE | re.DOTALL)
    
    # 9. Monto Neto (tolerar puntos/comas, $)
    question = "¿Cuál es el monto neto?"
    monto_neto_raw = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:Neto|MONTO NETO)\s*[:\s]*\$?([\d.,]+)')
    fields['monto_neto'] = float(re.sub(r'[.,]', '', monto_neto_raw)) if monto_neto_raw else None
    
    # 10. IVA (captura 19% o valor)
    question = "¿Cuál es el tipo o porcentaje de IVA?"
    iva_raw = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:IVA|I\.V\.A\.)\s*(\d+\.?\d*)%?')
    fields['iva_tipo'] = float(iva_raw.replace('%', '')) / 100 if iva_raw and '%' in iva_raw else (float(iva_raw) if iva_raw else None)
    
    # 11. Total
    question = "¿Cuál es el total?"
    total_raw = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:Total|TOTAL)\s*[:\s]*\$?([\d.,]+)')
    fields['total'] = float(re.sub(r'[.,]', '', total_raw)) if total_raw else None
    
    # Log resultados
    missing = [k for k, v in fields.items() if v is None]
    if missing:
        logger.warning(f"Campos missing: {missing}. Considera mejorar preguntas o regex.")
    else:
        logger.info("Todos los campos extraídos exitosamente.")
    
    return fields

# Ejemplo de uso
if __name__ == "__main__":
    # Usa el texto revuelto del log como sample
    sample_text = "R.U.T.:76.869.695- 0\nDEPROX SPA\n... "  # Pega el texto completo del log aquí
    parsed = parse_invoice_text(sample_text)
    print(parsed)