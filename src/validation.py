import logging
import re
from datetime import datetime
from typing import Dict, Tuple, Optional

# Configura logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Diccionario de meses en español
MESES_ESPANOL = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

def validate_rut(rut: str) -> bool:
    """
    Valida un RUT chileno con el algoritmo de dígito verificador (módulo 11).
    """
    rut = rut.replace(".", "").replace("-", "").upper()
    if not re.match(r'^\d{1,8}[0-9K]$', rut):
        return False
    
    body, dv = rut[:-1], rut[-1]
    sum = 0
    mul = 2
    for char in reversed(body):
        sum += int(char) * mul
        mul = mul + 1 if mul < 7 else 2
    
    mod = sum % 11
    calc_dv = 11 - mod if mod != 0 else 0
    calc_dv = 'K' if calc_dv == 10 else str(calc_dv)
    
    return calc_dv == dv

def validate_date(date_str: str) -> bool:
    """
    Valida fecha: Primero intenta numérico DD-MM-YYYY, luego textual 'DD de MES de YYYY'.
    Si válida, loguea el formato detectado.
    """
    # Intento numérico
    try:
        datetime.strptime(date_str, "%d-%m-%Y")
        logger.info(f"Fecha numérica válida: {date_str}")
        return True
    except ValueError:
        pass
    
    # Intento textual
    date_str_lower = date_str.lower().strip()
    match = re.match(r'(\d{1,2}) (de )?([a-z]+) (de )?(\d{4})', date_str_lower)
    if match:
        day, _, month_name, _, year = match.groups()
        month = MESES_ESPANOL.get(month_name)
        if month:
            try:
                datetime(int(year), month, int(day))
                logger.info(f"Fecha textual válida: {date_str} (normalizada a {day.zfill(2)}-{str(month).zfill(2)}-{year})")
                return True
            except ValueError:
                pass
    
    logger.warning(f"Fecha inválida: {date_str}")
    return False

def validate_invoice_data(data: Dict[str, any], previous_invoice_num: Optional[int] = None, iva_rate: float = 0.19) -> Tuple[bool, Dict[str, str]]:
    """
    Valida los campos mínimos de una factura chilena.
    """
    required_fields = [
        'numero_factura', 'fecha_emision', 'nombre_emisor', 'nombre_destinatario',
        'rut_emisor', 'domicilio_emisor', 'domicilio_destinatario',
        'descripcion_operaciones', 'monto_neto', 'iva_tipo', 'total'
    ]
    
    errors = {}
    
    # Chequeo de presencia
    for field in required_fields:
        if field not in data or data[field] is None:
            errors[field] = f"Campo requerido '{field}' faltante o vacío."
    
    if errors:
        logger.warning(f"Validación fallida por campos faltantes: {errors}")
        return False, errors
    
    # Validaciones específicas
    try:
        # 1. Número factura
        num_factura = int(data['numero_factura'])
        if num_factura <= 0:
            errors['numero_factura'] = "Debe ser un número positivo."
        if previous_invoice_num is not None and num_factura != previous_invoice_num + 1:
            errors['numero_factura'] = f"No es correlativo (esperado: {previous_invoice_num + 1})."
        
        # 2. Fecha (usa la función expandida)
        if not validate_date(data['fecha_emision']):
            errors['fecha_emision'] = "Formato inválido (esperado: DD-MM-YYYY o 'DD de MES de YYYY')."
        
        # 3-4,6-7,8: Strings
        for field in ['nombre_emisor', 'nombre_destinatario', 'domicilio_emisor', 'domicilio_destinatario', 'descripcion_operaciones']:
            if not isinstance(data[field], str) or len(data[field]) < 3:
                errors[field] = "Debe ser un string válido con al menos 3 caracteres."
        
        # 5. RUT
        if not validate_rut(data['rut_emisor']):
            errors['rut_emisor'] = "RUT inválido."
        
        # 9. Monto Neto
        monto_neto = float(data['monto_neto'])
        if monto_neto <= 0:
            errors['monto_neto'] = "Debe ser positivo."
        
        # 10. IVA
        iva_tipo = float(data['iva_tipo'])
        if iva_tipo < 0 or iva_tipo > 1:
            errors['iva_tipo'] = "Debe ser entre 0 y 1 (ej. 0.19)."
        if iva_tipo != iva_rate:
            logger.warning(f"IVA no estándar ({iva_tipo} vs {iva_rate}); permitiendo.")
        
        # 11. Total
        total = float(data['total'])
        expected_total = monto_neto * (1 + iva_tipo)
        if abs(total - expected_total) > 0.01:
            errors['total'] = f"No coincide con cálculo (esperado: {expected_total:.2f})."
    
    except ValueError as ve:
        errors['general'] = f"Error de conversión: {ve}"
    
    if errors:
        logger.error(f"Validación fallida: {errors}")
        return False, errors
    
    logger.info("Validación exitosa.")
    return True, {}

# Ejemplo de uso
if __name__ == "__main__":
    sample_data = {
        'numero_factura': '123',
        'fecha_emision': '26 de julio de 2020',  # Ahora maneja esto
        'nombre_emisor': 'Empresa Emisora SPA',
        'nombre_destinatario': 'Cliente Destinatario Ltda',
        'rut_emisor': '76.123.456-7',
        'domicilio_emisor': 'Av. Siempre Viva 123, Santiago',
        'domicilio_destinatario': 'Calle Falsa 456, Valparaíso',
        'descripcion_operaciones': 'Venta de productos electrónicos',
        'monto_neto': 100000.0,
        'iva_tipo': 0.19,
        'total': 119000.0
    }
    valid, errs = validate_invoice_data(sample_data, previous_invoice_num=122)
    print("Válido:", valid)
    print("Errores:", errs)