import os
import re
from dotenv import load_dotenv
from datetime import date
from factura import Factura
from tipo_factura import TipoFactura

load_dotenv()
HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
# if not HF_TOKEN:
#     raise ValueError("HUGGINGFACE_TOKEN no encontrado en .env. Crea uno en huggingface.co/settings/tokens.")

class FacturaExtractor:
    """
    Extractor inteligente de campos en facturas chilenas.
    Analiza texto OCR de facturas y extrae información estructurada.
    """
    
    def __init__(self):
        """Inicializa el extractor con patrones regex predefinidos"""
        # Patrón para RUT chileno: XX.XXX.XXX-X o XXXXXXXX-X (con posibles espacios)
        # Captura: XX.XXX.XXX-\s*X o XX.XXX.XXX- X
        self.rut_pattern = r'(\d{1,2}\.\d{3}\.\d{3}-\s*[\dkK]|\d{8}-\s*[\dkK])'
        
    def extract_ruts(self, text):
        """
        Extrae los RUT (número de identificación fiscal) del texto.
        Retorna el primero como emisor y el segundo como destinatario.
        
        Args:
            text (str): Texto extraído del PDF
            
        Returns:
            dict: {'emisor': 'XX.XXX.XXX-X', 'destinatario': 'XX.XXX.XXX-X'}
        """
        # Buscar todos los RUT en el texto (con y sin puntos)
        ruts = re.findall(self.rut_pattern, text, re.IGNORECASE)
        
        # Normalizar RUT (remover espacios extra después del guión)
        ruts_limpios = []
        
        for rut in ruts:
            rut = re.sub(r'\s*-\s*', '-', rut) # Remover espacios alrededor del guión
            rut = rut.upper() # Convertir a mayúsculas (K de verificador)
            ruts_limpios.append(rut)
        
        # Eliminar duplicados manteniendo orden
        ruts_unicos = []
        for rut in ruts_limpios:
            if rut not in ruts_unicos:
                ruts_unicos.append(rut)
        
        return {
            'emisor': ruts_unicos[0] if len(ruts_unicos) > 0 else "",
            'destinatario': ruts_unicos[1] if len(ruts_unicos) > 1 else "",
            'ruts_encontrados': ruts_unicos
        }
    
    def extract_numero_factura(self, text):
        """
        Extrae el número de factura.
        Busca patrones como "N°XXX", "N° XXX", "FACTURA N° XXX", etc.
        Soporta números de factura con cualquier cantidad de cifras.
        
        Args:
            text (str): Texto extraído del PDF
            
        Returns:
            int: Número de factura o 0 si no se encuentra
        """
        # Patrones comunes para número de factura (sin limitación de cifras)
        patterns = [
            r'FACTURA\s+[Nn]°\s*(\d+)',       # FACTURA N° XXX
            r'(?:^|[\s])[Nn]°\s*(\d+)',       # N° XXX (inicio o después de espacio)
            r'[Nn]úmero\s+(?:de\s+)?Factura[:\s]*(\d+)',  # Número de Factura: XXX
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                numero = match.group(1).strip()
                if numero:
                    return int(numero)
        
        return 0
    
    def extract_fecha_emision(self, text):
        """
        Extrae la fecha de emisión.
        Busca patrones como "Fecha Emision: 06 de Julio del 2023"
        
        Args:
            text (str): Texto extraído del PDF
            
        Returns:
            date: Fecha como objeto date o date(1900, 1, 1) si no se encuentra
        """
        meses_map = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        # Patrones para fecha de emisión
        patterns = [
            r'[Ff]echa\s+[Ee]misio?n[:\s]+(\d{1,2})\s+de\s+(\w+)\s+del?\s+(\d{4})',
            r'[Ff]echa[:\s]+(\d{1,2})/(\d{1,2})/(\d{4})',
            r'[Ee]mision[:\s]+(\d{1,2})\s+de\s+(\w+)\s+del?\s+(\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    if len(groups) == 3:
                        dia, mes, año = groups
                        # Si mes es palabra ("Julio"), convertir a número
                        if mes.isdigit():
                            mes_num = int(mes)
                        else:
                            mes_num = meses_map.get(mes.lower())
                        if mes_num:
                            return date(int(año), mes_num, int(dia))
                except (ValueError, KeyError):
                    continue
        
        return date(1900, 1, 1)
    
    def extract_empresa_emisora(self, text):
        """
        Extrae el nombre de la empresa emisora.
        Es la primera línea con formato de nombre (mayúsculas) después del RUT.
        
        Args:
            text (str): Texto extraído del PDF
            
        Returns:
            str: Nombre de la empresa o string vacío si no se encuentra
        """
        # Buscar línea con nombre de empresa (mayúsculas y palabras)
        # Patrón: RUT en primera línea, empresa en segunda línea
        matches = re.search(r'^R\.?U\.?T.*?\n+\s*([A-Z][A-Z\s\.]+?)(?:\n)', text, re.MULTILINE | re.DOTALL)
        
        if matches:
            empresa = matches.group(1).strip()
            # Normalizar
            empresa = re.sub(r'\s+', ' ', empresa)
            if empresa and len(empresa) > 2:
                return empresa
        
        return ""
    
    def extract_empresa_destinataria(self, text):
        """
        Extrae el nombre de la empresa destinataria.
        Busca después de "SENOR(ES):" o "CLIENTE:".
        
        Args:
            text (str): Texto extraído del PDF
            
        Returns:
            str: Nombre de la empresa o string vacío si no se encuentra
        """
        # Buscar empresa destinataria - generalmente después de SENOR(ES):
        patterns = [
            r'SENOR\s*\(?\s*ES\s*\)?\s*[:\s]+([A-Z][A-Z\s\.]+?)(?:\n|R\.U\.T)',
            r'SEÑOR\s*\(?\s*ES\s*\)?\s*[:\s]+([A-Z][A-Z\s\.]+?)(?:\n|R\.U\.T)',
            r'CLIENTE[:\s]+([A-Z][A-Z\s\.]+?)(?:\n|R\.U\.T)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                empresa = match.group(1).strip()
                # Limpiar
                empresa = re.sub(r'\s+', ' ', empresa)
                if empresa and len(empresa) > 2:
                    return empresa
        
        return ""
    
    def extract_domicilios(self, text):
        """
        Extrae domicilios del emisor y destinatario.
        - Domicilio emisor: línea con dirección en la sección del emisor (antes de SENOR(ES):)
        - Domicilio destinatario: línea con DIRECCION: o en la sección del destinatario
        
        Args:
            text (str): Texto extraído del PDF
            
        Returns:
            dict: {'emisor': 'domicilio', 'destinatario': 'domicilio'}
        """
        domicilios = {'emisor': "", 'destinatario': ""}
        
        # Dividir en dos secciones: antes y después de SENOR(ES):
        senor_match = re.search(r'SENOR\s*\(?\s*ES\s*\)?', text, re.IGNORECASE)
        
        if senor_match:
            # Sección emisor: antes de SENOR(ES):
            seccion_emisor = text[:senor_match.start()]
            # Sección destinatario: después de SENOR(ES):
            seccion_destinatario = text[senor_match.start():]
        else:
            seccion_emisor = text
            seccion_destinatario = text
        
        # Buscar domicilio emisor
        # Patrón: línea con guión que contiene caracteres alfanuméricos (típico de direcciones)
        # Excluir líneas que tengan "N°" (número de factura) al final
        direcciones_emisor = re.findall(r'^([A-Z][A-Z0-9\s]+\d[A-Z0-9\s\-,]*?)(?:\s+N°\d+)?(?:\n|$)', seccion_emisor, re.MULTILINE)
        
        if direcciones_emisor:
            # Tomar la última que sea válida
            for dir_candidate in reversed(direcciones_emisor):
                dir_clean = re.sub(r'\s+N°\d+\s*$', '', dir_candidate).strip()
                if len(dir_clean) > 5 and not any(x in dir_clean for x in ['SENOR', 'Giro:', 'eMail', 'Telefono', 'TIPO']):
                    domicilios['emisor'] = self._clean_domicilio(dir_clean)
                    break
        
        # Buscar domicilio destinatario (DIRECCION:)
        direccion_pattern = r'DIRECCI[OÓ]N\s*:\s*([^\n]+)'
        dir_match = re.search(direccion_pattern, seccion_destinatario, re.IGNORECASE | re.MULTILINE)
        if dir_match:
            domicilios['destinatario'] = self._clean_domicilio(dir_match.group(1))
        
        return domicilios
    
    def _clean_domicilio(self, domicilio):
        """
        Limpia y normaliza un domicilio.
        
        Args:
            domicilio (str): Domicilio a limpiar
            
        Returns:
            str: Domicilio limpiado
        """
        domicilio = re.sub(r'\s+', ' ', domicilio) # Remover espacios múltiples
        domicilio = domicilio.replace('\n', ' ').strip() # Remover saltos de línea
        return domicilio
    
    def _parse_monto(self, monto_str):
        """
        Convierte un string de monto en entero.
        Maneja formatos como "123.456.789" o "123,456.789"
        
        Args:
            monto_str (str): String del monto
            
        Returns:
            int: Valor numérico o 0 si no se puede parsear
        """
        if not monto_str:
            return 0
        try:
            # Remover espacios y $
            monto_str = monto_str.replace('$', '').replace(' ', '').strip()
            # Si usa puntos como separadores de miles (formato chileno)
            monto_str = monto_str.replace('.', '')
            # Convertir coma decimal a punto si existe
            monto_str = monto_str.replace(',', '.')
            return int(float(monto_str))
        except (ValueError, AttributeError):
            return 0
    
    def extract_montos(self, text):
        """
        Extrae montos: Neto, IVA y Total.
        Si no encuentra el total, lo calcula como Neto + IVA.
        
        Args:
            text (str): Texto extraído del PDF
            
        Returns:
            dict: {'neto': int, 'iva': int, 'total': int, 'impuesto_adicional': int}
        """
        montos = {'neto': 0, 'iva': 0, 'total': 0, 'impuesto_adicional': 0}
        
        # Buscar MONTO NETO
        neto_match = re.search(r'MONTO\s+NETO[:\s]*\$\s*=?\s*([\d.,]+)', text, re.IGNORECASE)
        if neto_match:
            neto_value = neto_match.group(1)
            montos['neto'] = self._parse_monto(neto_value) or 0
        
        # Buscar IVA (puede ser "I.V.A.19%", "IVA 19%", etc.)
        iva_matches = re.findall(r'I\.?V\.?A\.?[:\s]*\d+%?\s*\$\s*=?\s*([\d.,]+)', text, re.IGNORECASE)
        if iva_matches:
            iva_value = iva_matches[0]
            montos['iva'] = self._parse_monto(iva_value) or 0
        
        # Buscar TOTAL
        total_matches = re.findall(r'TOTAL[:\s]*\$\s*=?\s*([\d.,]+)', text, re.IGNORECASE)
        if total_matches:
            montos['total'] = self._parse_monto(total_matches[0]) or 0
        else:
            # Calcular total si no se encuentra
            if montos['neto'] > 0 or montos['iva'] > 0:
                montos['total'] = montos['neto'] + montos['iva']
        
        # Buscar IMPUESTO ADICIONAL
        impuesto_matches = re.findall(r'IMPUESTO\s+ADICIONAL[:\s]*\$\s*=?\s*([\d.,]+)', text, re.IGNORECASE)
        if impuesto_matches:
            imp_value = self._parse_monto(impuesto_matches[0])
            # Solo asignar si es mayor a 0
            if imp_value and imp_value > 0:
                montos['impuesto_adicional'] = imp_value
        
        return montos
    
    def extract_all(self, text, tipo_factura=None):
        """
        Extrae todos los campos de una factura y retorna una instancia de Factura.
        
        Args:
            text (str): Texto extraído del PDF
            tipo_factura (TipoFactura, optional): Tipo de factura (escaneada o digital)
            
        Returns:
            Factura: Instancia de Factura con todos los campos extraídos
        """
        ruts = self.extract_ruts(text)
        domicilios = self.extract_domicilios(text)
        montos = self.extract_montos(text)
        
        # Si no se proporciona tipo_factura, usar uno por defecto
        if tipo_factura is None:
            tipo_factura = TipoFactura()
        
        return Factura(
            numero_factura=self.extract_numero_factura(text),
            fecha_emision=self.extract_fecha_emision(text),
            empresa_emisora=self.extract_empresa_emisora(text),
            empresa_destinataria=self.extract_empresa_destinataria(text),
            rut_emisor=ruts['emisor'],
            rut_destinatario=ruts['destinatario'],
            domicilio_emisor=domicilios['emisor'],
            domicilio_destinatario=domicilios['destinatario'],
            monto_neto=montos['neto'],
            iva=montos['iva'],
            total=montos['total'],
            impuesto_adicional=montos['impuesto_adicional'],
            tipo_factura=tipo_factura,
        )