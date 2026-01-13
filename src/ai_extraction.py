import os
import re
from dotenv import load_dotenv
from datetime import datetime

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
        ruts_limpios = [self._normalize_rut(rut) for rut in ruts]
        
        # Eliminar duplicados manteniendo orden
        ruts_unicos = []
        for rut in ruts_limpios:
            if rut not in ruts_unicos:
                ruts_unicos.append(rut)
        
        return {
            'emisor': ruts_unicos[0] if len(ruts_unicos) > 0 else None,
            'destinatario': ruts_unicos[1] if len(ruts_unicos) > 1 else None,
            'ruts_encontrados': ruts_unicos
        }
    
    def _normalize_rut(self, rut):
        """
        Normaliza un RUT removiendo espacios adicionales.
        
        Args:
            rut (str): RUT a normalizar (puede tener espacios)
            
        Returns:
            str: RUT normalizado
        """
        # Remover espacios alrededor del guión
        rut = re.sub(r'\s*-\s*', '-', rut)
        # Convertir a mayúsculas (K de verificador)
        rut = rut.upper()
        return rut
    
    def extract_numero_factura(self, text):
        """
        Extrae el número de factura.
        Busca patrones como "N°XXX", "N° XXX", "FACTURA N° XXX", etc.
        
        Args:
            text (str): Texto extraído del PDF
            
        Returns:
            str: Número de factura o None
        """
        # Patrones comunes para número de factura
        patterns = [
            r'(?:FACTURA\s+)?[Nn]°\s*(\d+)',  # N° 183
            r'(?:^|[\s])([Nn]°\s*\d+)',        # N° 338
            r'Factura.*?[Nn]°\s*(\d+)',        # Factura N°XXX
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extraer solo el número
                numero = re.search(r'\d+', match.group(1) if match.groups() else match.group())
                if numero:
                    return f"N°{numero.group()}"
        
        return None
    
    def extract_fecha_emision(self, text):
        """
        Extrae la fecha de emisión.
        Busca patrones como "Fecha Emision: 06 de Julio del 2023"
        
        Args:
            text (str): Texto extraído del PDF
            
        Returns:
            str: Fecha en formato original o None
        """
        # Patrones para fecha de emisión
        patterns = [
            r'[Ff]echa\s+[Ee]misio?n[:\s]+(\d{1,2}\s+de\s+\w+\s+del?\s+\d{4})',
            r'[Ff]echa[:\s]+(\d{1,2}/\d{1,2}/\d{4})',
            r'[Ee]mision[:\s]+(\d{1,2}\s+de\s+\w+\s+del?\s+\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_empresa_emisora(self, text):
        """
        Extrae el nombre de la empresa emisora.
        Es la primera línea con formato de nombre (mayúsculas) después del RUT.
        
        Args:
            text (str): Texto extraído del PDF
            
        Returns:
            str: Nombre de la empresa o None
        """
        # Buscar línea con nombre de empresa (mayúsculas y palabras)
        # Generalmente: SPA, S.A., S.L., etc. o nombres con varias palabras en mayúsculas
        # Patrón: RUT en primera línea, empresa en segunda línea
        matches = re.search(r'^R\.?U\.?T.*?\n+\s*([A-Z][A-Z\s\.]+?)(?:\n)', text, re.MULTILINE | re.DOTALL)
        
        if matches:
            empresa = matches.group(1).strip()
            # Normalizar
            empresa = re.sub(r'\s+', ' ', empresa)
            if empresa and len(empresa) > 2:
                return empresa
        
        return None
    
    def extract_empresa_destinataria(self, text):
        """
        Extrae el nombre de la empresa destinataria.
        Busca después de "SENOR(ES):" o "CLIENTE:".
        
        Args:
            text (str): Texto extraído del PDF
            
        Returns:
            str: Nombre de la empresa o None
        """
        # Buscar empresa destinataria - generalmente después de SENOR(ES):
        patterns = [
            r'SENOR\s*\(?\s*ES\s*\)?\s*[:\s]+([A-Z][A-Z\s\.]+?)(?:\n|R\.U\.T)',
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
        
        return None
    
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
        domicilios = {'emisor': None, 'destinatario': None}
        
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
        # Remover espacios múltiples
        domicilio = re.sub(r'\s+', ' ', domicilio)
        # Remover saltos de línea
        domicilio = domicilio.replace('\n', ' ').strip()
        return domicilio
    
    def extract_descripcion_operaciones(self, text):
        """
        Extrae la descripción de operaciones/servicios.
        Busca la línea de descripción del producto o servicio.
        
        Args:
            text (str): Texto extraído del PDF
            
        Returns:
            str: Descripción de operaciones o None
        """
        # Buscar descripción entre líneas de detalle
        patterns = [
            # Buscar líneas que comiencen con "Estado de Pago" u "EPN°" y capturar la descripción
            r'(?:Estado de Pago n°|EPN°)[^\n]*\n(?:\s*[A-Z][^\n]*\n)*\s*([A-Z][A-Za-z\s\.áéíóúñ]+?)(?:\n\s*-|\n\s*MONTO|\n\s*IMPUESTO|$)',
            # Alternativa: buscar en la sección de "Descripcion Cantidad"
            r'(?:Estado de Pago|EPN°)[^\n]*\s+(.+?)(?:\nObras|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                descripcion = match.group(1).strip()
                # Limpiar: remover números de cantidad, etc.
                descripcion = re.sub(r'\s*un\s+\d+', '', descripcion)
                descripcion = re.sub(r'\s+', ' ', descripcion)
                if len(descripcion) > 3:
                    return descripcion
        
        return None
    
    def extract_montos(self, text):
        """
        Extrae montos: Neto, IVA y Total.
        Si no encuentra el total, lo calcula como Neto + IVA.
        
        Args:
            text (str): Texto extraído del PDF
            
        Returns:
            dict: {'neto': 'valor', 'iva': 'valor', 'total': 'valor', 'impuesto_adicional': 'valor'}
        """
        montos = {'neto': None, 'iva': None, 'total': None, 'impuesto_adicional': None}
        
        # Patrón para encontrar montos ($ X.XXX.XXX o $X.XXX.XXX o $= X.XXX.XXX)
        monto_pattern = r'\$\s*=?\s*([\d.,]+)'
        
        # Buscar MONTO NETO
        neto_match = re.search(r'MONTO\s+NETO[:\s]*\$\s*=?\s*([\d.,]+)', text, re.IGNORECASE)
        if neto_match:
            neto_value = neto_match.group(1)
            montos['neto'] = f"${neto_value}"
        
        # Buscar IVA (puede ser "I.V.A.19%", "IVA 19%", etc.)
        iva_matches = re.findall(r'I\.?V\.?A\.?[:\s]*\d+%?\s*\$\s*=?\s*([\d.,]+)', text, re.IGNORECASE)
        if iva_matches:
            iva_value = iva_matches[0]
            montos['iva'] = f"${iva_value}"
        
        # Buscar TOTAL
        total_matches = re.findall(r'TOTAL[:\s]*\$\s*=?\s*([\d.,]+)', text, re.IGNORECASE)
        if total_matches:
            montos['total'] = f"${total_matches[0]}"
        else:
            # Calcular total si no se encuentra
            if montos['neto'] and montos['iva']:
                try:
                    # Extraer números sin $ ni puntos
                    neto_num = float(montos['neto'].replace('$', '').replace('.', '').replace(',', '.'))
                    iva_num = float(montos['iva'].replace('$', '').replace('.', '').replace(',', '.'))
                    total_num = neto_num + iva_num
                    # Formatear con separadores
                    total_str = f"{total_num:,.0f}".replace(',', '.')
                    montos['total'] = f"${total_str}"
                except:
                    pass
        
        # Buscar IMPUESTO ADICIONAL
        impuesto_matches = re.findall(r'IMPUESTO\s+ADICIONAL[:\s]*\$\s*=?\s*([\d.,]+)', text, re.IGNORECASE)
        if impuesto_matches:
            imp_value = impuesto_matches[0]
            # Solo mostrar si es mayor a 0
            if imp_value not in ['0', '0.', '0,']:
                montos['impuesto_adicional'] = f"${imp_value}"
        
        return montos
    
    def extract_all(self, text):
        """
        Extrae todos los campos de una factura.
        
        Args:
            text (str): Texto extraído del PDF
            
        Returns:
            dict: Diccionario con todos los campos extraídos
        """
        ruts = self.extract_ruts(text)
        domicilios = self.extract_domicilios(text)
        montos = self.extract_montos(text)
        
        factura = {
            'numero_factura': self.extract_numero_factura(text),
            'fecha_emision': self.extract_fecha_emision(text),
            'empresa_emisora': self.extract_empresa_emisora(text),
            'empresa_destinataria': self.extract_empresa_destinataria(text),
            'rut_emisor': ruts['emisor'],
            'rut_destinatario': ruts['destinatario'],
            'domicilio_emisor': domicilios['emisor'],
            'domicilio_destinatario': domicilios['destinatario'],
            'descripcion_operaciones': self.extract_descripcion_operaciones(text),
            'monto_neto': montos['neto'],
            'iva': montos['iva'],
            'total': montos['total'],
            'impuesto_adicional': montos['impuesto_adicional'],
        }
        
        return factura
    
    def format_factura(self, factura):
        """
        Formatea la factura extraída de forma legible.
        
        Args:
            factura (dict): Diccionario con datos de la factura
            
        Returns:
            str: Texto formateado
        """
        output = []
        output.append("=" * 80)
        output.append("DATOS EXTRAÍDOS DE LA FACTURA")
        output.append("=" * 80)
        
        # Encabezado
        output.append(f"\nNúmero de Factura: {factura['numero_factura'] or '[No detectado]'}")
        output.append(f"Fecha de Emisión: {factura['fecha_emision'] or '[No detectado]'}")
        
        # Empresa Emisora
        output.append("\n" + "-" * 80)
        output.append("EMPRESA EMISORA")
        output.append("-" * 80)
        output.append(f"  Nombre: {factura['empresa_emisora'] or '[No detectado]'}")
        output.append(f"  RUT: {factura['rut_emisor'] or '[No detectado]'}")
        output.append(f"  Domicilio: {factura['domicilio_emisor'] or '[No detectado]'}")
        
        # Empresa Destinataria
        output.append("\n" + "-" * 80)
        output.append("EMPRESA DESTINATARIA")
        output.append("-" * 80)
        output.append(f"  Nombre: {factura['empresa_destinataria'] or '[No detectado]'}")
        output.append(f"  RUT: {factura['rut_destinatario'] or '[No detectado]'}")
        output.append(f"  Domicilio: {factura['domicilio_destinatario'] or '[No detectado]'}")
        
        # Descripción de Operaciones
        output.append("\n" + "-" * 80)
        output.append("DESCRIPCIÓN DE OPERACIONES")
        output.append("-" * 80)
        output.append(f"{factura['descripcion_operaciones'] or '[No detectado]'}")
        
        # Montos
        output.append("\n" + "-" * 80)
        output.append("MONTOS")
        output.append("-" * 80)
        output.append(f"  Monto Neto: {factura['monto_neto'] or '[No detectado]'}")
        output.append(f"  IVA (19%): {factura['iva'] or '[No detectado]'}")
        if factura['impuesto_adicional']:
            output.append(f"  Impuesto Adicional: {factura['impuesto_adicional']}")
        output.append(f"  TOTAL: {factura['total'] or '[No detectado]'}")
        
        output.append("\n" + "=" * 80)
        
        return "\n".join(output)