"""
Servicio de extracción inteligente de campos de facturas.
Analiza texto OCR y extrae información estructurada usando regex.
"""
import re
import logging
from datetime import date
from typing import Dict, Any

logger = logging.getLogger(__name__)


class FacturaExtractorService:
    """
    Extractor inteligente de campos en facturas chilenas.
    Analiza texto y extrae información estructurada.
    """
    
    def __init__(self):
        """Inicializa el extractor con patrones regex predefinidos"""
        # Patrón para RUT chileno: XX.XXX.XXX-X o XXXXXXXX-X
        self.rut_pattern = r'(\d{1,2}\.\d{3}\.\d{3}-\s*[\dkK]|\d{8}-\s*[\dkK])'
        logger.info("FacturaExtractorService initialized")
    
    def extract_ruts(self, text: str) -> Dict[str, Any]:
        """
        Extrae los RUT del texto.
        Retorna el primero como emisor y el segundo como destinatario.
        
        Args:
            text: Texto extraído del PDF
            
        Returns:
            dict: {'emisor': 'XX.XXX.XXX-X', 'destinatario': 'XX.XXX.XXX-X', 'ruts_encontrados': [...]}
        """
        # Buscar todos los RUT
        ruts = re.findall(self.rut_pattern, text, re.IGNORECASE)
        
        # Normalizar RUT (remover espacios alrededor del guión)
        ruts_limpios = []
        for rut in ruts:
            rut = re.sub(r'\s*-\s*', '-', rut)  # Normalizar guión
            rut = rut.upper()  # K mayúscula
            if rut not in ruts_limpios:  # Evitar duplicados
                ruts_limpios.append(rut)
        
        logger.debug(f"Found {len(ruts_limpios)} unique RUTs")
        
        return {
            'emisor': ruts_limpios[0] if len(ruts_limpios) > 0 else "",
            'destinatario': ruts_limpios[1] if len(ruts_limpios) > 1 else "",
            'ruts_encontrados': ruts_limpios
        }
    
    def extract_numero_factura(self, text: str) -> int:
        """
        Extrae el número de factura.
        Busca patrones como "N°XXX", "FACTURA N° XXX", etc.
        
        Args:
            text: Texto extraído del PDF
            
        Returns:
            Número de factura o 0 si no se encuentra
        """
        patterns = [
            r'FACTURA\s+[Nn]°\s*(\d+)',
            r'(?:^|[\s])[Nn]°\s*(\d+)',
            r'[Nn]úmero\s+(?:de\s+)?Factura[:\s]*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                numero = int(match.group(1))
                logger.debug(f"Found invoice number: {numero}")
                return numero
        
        logger.warning("Invoice number not found")
        return 0
    
    def extract_fecha_emision(self, text: str) -> date:
        """
        Extrae la fecha de emisión.
        Busca patrones como "Fecha Emision: 06 de Julio del 2023"
        
        Args:
            text: Texto extraído del PDF
            
        Returns:
            Fecha como objeto date o date(1900, 1, 1) si no se encuentra
        """
        meses_map = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        patterns = [
            r'[Ff]echa\s+[Ee]misio?n[:\s]+(\d{1,2})\s+de\s+(\w+)\s+del?\s+(\d{4})',
            r'[Ff]echa[:\s]+(\d{1,2})/(\d{1,2})/(\d{4})',
            r'[Ee]mision[:\s]+(\d{1,2})\s+de\s+(\w+)\s+del?\s+(\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    grupos = match.groups()
                    
                    # Formato con mes en texto
                    if len(grupos) == 3 and grupos[1].lower() in meses_map:
                        dia = int(grupos[0])
                        mes = meses_map[grupos[1].lower()]
                        anio = int(grupos[2])
                        fecha = date(anio, mes, dia)
                        logger.debug(f"Found date: {fecha}")
                        return fecha
                    # Formato dd/mm/yyyy
                    elif len(grupos) == 3:
                        dia = int(grupos[0])
                        mes = int(grupos[1])
                        anio = int(grupos[2])
                        fecha = date(anio, mes, dia)
                        logger.debug(f"Found date: {fecha}")
                        return fecha
                except (ValueError, IndexError) as e:
                    logger.warning(f"Error parsing date: {e}")
                    continue
        
        logger.warning("Date not found")
        return date(1900, 1, 1)
    
    def extract_empresa_emisora(self, text: str) -> str:
        """
        Extrae el nombre de la empresa emisora.
        
        Args:
            text: Texto extraído del PDF
            
        Returns:
            Nombre de la empresa o string vacío
        """
        # Buscar línea con nombre de empresa después de RUT
        matches = re.search(
            r'^R\.?U\.?T.*?\n+\s*([A-Z][A-Z\s\.]+?)(?:\n)',
            text,
            re.MULTILINE | re.DOTALL
        )
        
        if matches:
            empresa = matches.group(1).strip()
            # Normalizar espacios
            empresa = re.sub(r'\s+', ' ', empresa)
            if empresa and len(empresa) > 2:
                logger.debug(f"Found issuer: {empresa}")
                return empresa
        
        logger.warning("Issuer company not found")
        return ""
    
    def extract_empresa_destinataria(self, text: str) -> str:
        """
        Extrae el nombre de la empresa destinataria.
        
        Args:
            text: Texto extraído del PDF
            
        Returns:
            Nombre de la empresa o string vacío
        """
        patterns = [
            r'SENOR\s*\(?\s*ES\s*\)?\s*[:\s]+([A-Z][A-Z\s\.]+?)(?:\n|R\.U\.T)',
            r'SEÑOR\s*\(?\s*ES\s*\)?\s*[:\s]+([A-Z][A-Z\s\.]+?)(?:\n|R\.U\.T)',
            r'CLIENTE[:\s]+([A-Z][A-Z\s\.]+?)(?:\n|R\.U\.T)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                empresa = match.group(1).strip()
                empresa = re.sub(r'\s+', ' ', empresa)
                if empresa and len(empresa) > 2:
                    logger.debug(f"Found recipient: {empresa}")
                    return empresa
        
        logger.warning("Recipient company not found")
        return ""
    
    def extract_domicilios(self, text: str) -> Dict[str, str]:
        """
        Extrae domicilios del emisor y destinatario.
        
        Args:
            text: Texto extraído del PDF
            
        Returns:
            dict: {'emisor': 'domicilio', 'destinatario': 'domicilio'}
        """
        domicilios = {'emisor': "", 'destinatario': ""}
        
        # Dividir en secciones
        senor_match = re.search(r'SENOR\s*\(?\s*ES\s*\)?', text, re.IGNORECASE)
        
        if senor_match:
            seccion_emisor = text[:senor_match.start()]
            seccion_destinatario = text[senor_match.start():]
        else:
            seccion_emisor = text
            seccion_destinatario = text
        
        # Buscar domicilio emisor
        direcciones_emisor = re.findall(
            r'^([A-Z][A-Z0-9\s]+\d[A-Z0-9\s\-,]*?)(?:\s+N°\d+)?(?:\n|$)',
            seccion_emisor,
            re.MULTILINE
        )
        
        if direcciones_emisor:
            for dir_candidate in direcciones_emisor:
                if len(dir_candidate) > 10 and 'FACTURA' not in dir_candidate:
                    domicilios['emisor'] = self._clean_domicilio(dir_candidate)
                    break
        
        # Buscar domicilio destinatario
        direccion_pattern = r'DIRECCI[OÓ]N\s*:\s*([^\n]+)'
        dir_match = re.search(direccion_pattern, seccion_destinatario, re.IGNORECASE)
        if dir_match:
            domicilios['destinatario'] = self._clean_domicilio(dir_match.group(1))
        
        logger.debug(f"Found addresses - Issuer: {bool(domicilios['emisor'])}, Recipient: {bool(domicilios['destinatario'])}")
        return domicilios
    
    def _clean_domicilio(self, domicilio: str) -> str:
        """Limpia y normaliza un domicilio."""
        domicilio = re.sub(r'\s+', ' ', domicilio)
        domicilio = domicilio.replace('\n', ' ').strip()
        return domicilio
    
    def _parse_monto(self, monto_str: str) -> int:
        """
        Convierte un string de monto en entero.
        
        Args:
            monto_str: String del monto
            
        Returns:
            Valor numérico o 0
        """
        if not monto_str:
            return 0
        try:
            # Remover puntos y comas, quedarse solo con números
            monto_clean = re.sub(r'[^\d]', '', monto_str)
            return int(monto_clean) if monto_clean else 0
        except (ValueError, AttributeError):
            return 0
    
    def extract_montos(self, text: str) -> Dict[str, int]:
        """
        Extrae montos: Neto, IVA y Total.
        
        Args:
            text: Texto extraído del PDF
            
        Returns:
            dict: {'neto': int, 'iva': int, 'total': int, 'impuesto_adicional': int}
        """
        montos = {'neto': 0, 'iva': 0, 'total': 0, 'impuesto_adicional': 0}
        
        # Buscar MONTO NETO
        neto_match = re.search(r'MONTO\s+NETO[:\s]*\$\s*=?\s*([\d.,]+)', text, re.IGNORECASE)
        if neto_match:
            montos['neto'] = self._parse_monto(neto_match.group(1))
        
        # Buscar IVA
        iva_matches = re.findall(r'I\.?V\.?A\.?[:\s]*\d+%?\s*\$\s*=?\s*([\d.,]+)', text, re.IGNORECASE)
        if iva_matches:
            montos['iva'] = self._parse_monto(iva_matches[-1])
        
        # Buscar TOTAL
        total_matches = re.findall(r'TOTAL[:\s]*\$\s*=?\s*([\d.,]+)', text, re.IGNORECASE)
        if total_matches:
            montos['total'] = self._parse_monto(total_matches[-1])
        else:
            # Calcular como neto + IVA
            if montos['neto'] > 0:
                montos['total'] = montos['neto'] + montos['iva']
        
        # Buscar IMPUESTO ADICIONAL
        impuesto_matches = re.findall(r'IMPUESTO\s+ADICIONAL[:\s]*\$\s*=?\s*([\d.,]+)', text, re.IGNORECASE)
        if impuesto_matches:
            montos['impuesto_adicional'] = self._parse_monto(impuesto_matches[-1])
        
        logger.debug(f"Found amounts - Neto: {montos['neto']}, IVA: {montos['iva']}, Total: {montos['total']}")
        return montos
    
    def extract_all(self, text: str) -> Dict[str, Any]:
        """
        Extrae todos los campos de una factura.
        
        Args:
            text: Texto extraído del PDF
            
        Returns:
            Dict con todos los campos extraídos
        """
        logger.info("Extracting all invoice fields...")
        
        ruts = self.extract_ruts(text)
        domicilios = self.extract_domicilios(text)
        montos = self.extract_montos(text)
        
        result = {
            'numero_factura': self.extract_numero_factura(text),
            'fecha_emision': self.extract_fecha_emision(text),
            'empresa_emisora': self.extract_empresa_emisora(text),
            'empresa_destinataria': self.extract_empresa_destinataria(text),
            'rut_emisor': ruts['emisor'],
            'rut_destinatario': ruts['destinatario'],
            'domicilio_emisor': domicilios['emisor'],
            'domicilio_destinatario': domicilios['destinatario'],
            'monto_neto': montos['neto'],
            'iva': montos['iva'],
            'total': montos['total'],
            'impuesto_adicional': montos['impuesto_adicional'],
        }
        
        logger.info("Extraction completed successfully")
        return result


# Singleton instance
factura_extractor_service = FacturaExtractorService()
