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

def extract_field_with_qa(text: str, question: str, min_score: float = 0.3) -> Optional[str]:
    """
    Usa QA para extraer un campo preguntando al modelo.
    Retorna None si la confianza es baja.
    """
    try:
        result = qa_pipeline(question=question, context=text)
        answer = result['answer'].strip()
        score = result['score']
        
        if score > min_score and answer:
            logger.info(f"QA OK (score={score:.2f}): {answer[:50]}")
            return answer
        else:
            logger.debug(f"QA score bajo ({score:.2f}) para '{question}'.")
            return None
    except Exception as e:
        logger.error(f"Error en QA para '{question}': {e}")
        return None

def regex_fallback(text: str, pattern: str, flags: int = re.IGNORECASE) -> Optional[str]:
    """
    Fallback con regex, ahora soporta flags personalizados.
    Retorna el primer grupo capturado, o todo el match si no hay grupos.
    """
    match = re.search(pattern, text, flags=flags)
    if not match:
        return None
    try:
        return match.group(1).strip()
    except:
        return match.group(0).strip()

def extract_date_field(text: str, pattern: str, flags: int = re.IGNORECASE) -> Optional[str]:
    """
    Extrae fecha con múltiples grupos y los arma en formato normalizable.
    """
    match = re.search(pattern, text, flags=flags)
    if not match:
        return None
    
    groups = match.groups()
    if len(groups) >= 3:
        # Formato: día, mes, año
        return f"{groups[0]} de {groups[1]} de {groups[2]}"
    elif len(groups) >= 1:
        return groups[0].strip()
    return None

def parse_invoice_text(text: str) -> Dict[str, any]:
    fields = {}
    
    # 1. Número factura (captura después de FACTURA o Nº)
    question = "¿Cuál es el número o Nº de la factura?"
    # Mejorado: busca patrones más amplios
    fields['numero_factura'] = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:FACTURA|Nº|N\*|Número|N°)[:\s]*(\d+)', re.IGNORECASE)
    
    # 2. Fecha de emisión (REGEX PRIMERO - es más confiable para fechas)
    question = "¿Cuál es la fecha de emisión?"
    # Captura: "06 de Julio del 2023" o "06 de Julio de 2023"
    fecha_raw = extract_date_field(text, r'Fecha\s+Emisi[óo]n:\s*(\d{1,2})\s+de\s+([a-zA-Z]+)\s+del?\s+(\d{4})', re.IGNORECASE)
    fields['fecha_emision'] = normalize_date(fecha_raw) if fecha_raw else None
    
    # 3. Nombre emisor (buscar en primeras líneas o después de GIRO)
    question = "¿Cuál es el nombre o denominación del emisor o empresa emisora?"
    # Intenta primero al inicio, luego después de Giro
    nombre_emisor = extract_field_with_qa(text, question)
    if not nombre_emisor:
        nombre_emisor = regex_fallback(text, r'^([A-Z][A-Z0-9\s&\.]+?(?:SPA|SA|LTDA|EIRL|S\.A\.))\s*$', re.IGNORECASE | re.MULTILINE)
    if not nombre_emisor:
        # Si no está al inicio, buscar después de patrón similar
        nombre_emisor = regex_fallback(text, r'(?:Giro|GIRO)[:\s]*([^\n]+)', re.IGNORECASE)
    fields['nombre_emisor'] = nombre_emisor
    
    # 4. Nombre destinatario (aparece como "SEÑOR(ES):")
    question = "¿Cuál es el nombre o denominación del destinatario o cliente?"
    fields['nombre_destinatario'] = extract_field_with_qa(text, question) or regex_fallback(text, r'SE[ÑN]OR\s*\(\s*ES\s*\)\s*:\s*([^\n]+?)(?:\s*R\.?U\.?T\.?|\s*$)', re.IGNORECASE)
    
    # 5. RUT emisor (permite espacio antes del dígito verificador)
    question = "¿Cuál es el RUT del emisor?"
    rut_raw = extract_field_with_qa(text, question) or regex_fallback(text, r'R\.?U\.?T\.?\s*:\s*(\d{1,2}\.?\d{3}\.?\d{3}-?\s*[\dKk])', re.IGNORECASE)
    fields['rut_emisor'] = rut_raw.strip() if rut_raw else None
    
    # 6. Domicilio emisor
    question = "¿Cuál es el domicilio o dirección del emisor?"
    fields['domicilio_emisor'] = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:DOMICILIO|DIRECCI[OÓ]N|LAUTARO)\s*[:\s]*([^\n]+?)(?=\n|R\.?U\.?T|GIRO)', re.IGNORECASE)
    
    # 7. Domicilio destinatario (busca "GRAN BRETANA" o similar)
    question = "¿Cuál es el domicilio o dirección del destinatario?"
    fields['domicilio_destinatario'] = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:DIRECCI[OÓ]N|DOMICILIO)?\s*:\s*(GRAN\s+BRETANA[^\n]*?)(?:\n|COMUNA)', re.IGNORECASE)
    
    # 8. Descripción (captura entre "Estado de Pago" y "Referencias")
    question = "¿Cuál es la descripción de las operaciones o detalle?"
    fields['descripcion_operaciones'] = extract_field_with_qa(text, question) or regex_fallback(text, r'(?:Estado de Pago|Obras Civiles)(.*?)(?=Referencias|Forma de Pago|MONTO)', re.IGNORECASE | re.DOTALL)
    
    # 9. Monto Neto (busca "MONTO NETO" y el número)
    question = "¿Cuál es el monto neto?"
    monto_neto_raw = extract_field_with_qa(text, question) or regex_fallback(text, r'MONTO\s+NETO\s*\$?\s*([\d.,]+)', re.IGNORECASE)
    if monto_neto_raw:
        try:
            fields['monto_neto'] = float(re.sub(r'[\.,]', '', monto_neto_raw.replace('.', '').replace(',', '')))
        except:
            fields['monto_neto'] = None
    else:
        fields['monto_neto'] = None
    
    # 10. IVA (busca "IVA. 19%" o similar)
    question = "¿Cuál es el tipo o porcentaje de IVA?"
    iva_raw = extract_field_with_qa(text, question) or regex_fallback(text, r'I\.?V\.?A\.?\s*[:\s]*(\d+\.?\d*)%?', re.IGNORECASE)
    if iva_raw:
        try:
            iva_val = float(iva_raw.replace('%', '').strip())
            fields['iva_tipo'] = iva_val / 100 if iva_val > 1 else iva_val
        except:
            fields['iva_tipo'] = None
    else:
        fields['iva_tipo'] = None
    
    # 11. Total (busca "TOTAL" y el número)
    question = "¿Cuál es el total?"
    total_raw = extract_field_with_qa(text, question) or regex_fallback(text, r'TOTAL\s*\$?\s*([\d.,]+)', re.IGNORECASE)
    if total_raw:
        try:
            fields['total'] = float(re.sub(r'[\.,]', '', total_raw.replace('.', '').replace(',', '')))
        except:
            fields['total'] = None
    else:
        fields['total'] = None
    
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