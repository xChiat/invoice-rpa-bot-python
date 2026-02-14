from dataclasses import dataclass, field
from datetime import date
from tipo_factura import TipoFactura


@dataclass
class Factura:
    """
    Clase que representa una factura chilena con sus datos estructurados.
    Los montos se almacenan como enteros (sin separadores ni símbolos).
    Las fechas se almacenan como objetos date.
    No se usan Optional, se usan valores por defecto válidos.
    """
    numero_factura: int = 0
    fecha_emision: date = field(default_factory=lambda: date(1900, 1, 1))
    empresa_emisora: str = ""
    rut_emisor: str = ""
    domicilio_emisor: str = ""
    empresa_destinataria: str = ""
    rut_destinatario: str = ""
    domicilio_destinatario: str = ""
    monto_neto: int = 0
    iva: int = 0
    total: int = 0
    impuesto_adicional: int = 0
    tipo_factura: TipoFactura = field(default_factory=TipoFactura)
    
    def __str__(self) -> str:
        """
        Formatea la factura de forma legible usado en la consola.
        
        Returns:
            str: Texto formateado con los datos de la factura
        """
        output = []
        output.append("=" * 80)
        output.append("DATOS EXTRAÍDOS DE LA FACTURA")
        output.append("=" * 80)
        
        # Tipo de factura
        if self.tipo_factura and self.tipo_factura.tipo_factura:
            output.append(f"\nTipo de Factura: {self.tipo_factura.tipo_factura}")
        
        # Encabezado
        numero_str = f"N°{self.numero_factura}" if self.numero_factura > 0 else "[No detectado]"
        # Verificar si la fecha es la fecha por defecto (1900-01-01)
        fecha_valida = self.fecha_emision and self.fecha_emision.year != 1900
        fecha_str = self.fecha_emision.strftime("%d de %B del %Y") if fecha_valida else "[No detectado]"
        output.append(f"\nNúmero de Factura: {numero_str}")
        output.append(f"Fecha de Emisión: {fecha_str}")
        
        # Empresa Emisora
        output.append("\n" + "-" * 80)
        output.append("EMPRESA EMISORA")
        output.append("-" * 80)
        output.append(f"  Nombre: {self.empresa_emisora if self.empresa_emisora else '[No detectado]'}")
        output.append(f"  RUT: {self.rut_emisor if self.rut_emisor else '[No detectado]'}")
        output.append(f"  Domicilio: {self.domicilio_emisor if self.domicilio_emisor else '[No detectado]'}")
        
        # Empresa Destinataria
        output.append("\n" + "-" * 80)
        output.append("EMPRESA DESTINATARIA")
        output.append("-" * 80)
        output.append(f"  Nombre: {self.empresa_destinataria if self.empresa_destinataria else '[No detectado]'}")
        output.append(f"  RUT: {self.rut_destinatario if self.rut_destinatario else '[No detectado]'}")
        output.append(f"  Domicilio: {self.domicilio_destinatario if self.domicilio_destinatario else '[No detectado]'}")
        
        # Montos
        output.append("\n" + "-" * 80)
        output.append("MONTOS")
        output.append("-" * 80)
        
        neto_str = f"${self.monto_neto:,}".replace(",", ".") if self.monto_neto > 0 else "[No detectado]"
        iva_str = f"${self.iva:,}".replace(",", ".") if self.iva > 0 else "[No detectado]"
        total_str = f"${self.total:,}".replace(",", ".") if self.total > 0 else "[No detectado]"
        
        output.append(f"  Monto Neto: {neto_str}")
        output.append(f"  IVA (19%): {iva_str}")
        
        if self.impuesto_adicional > 0:
            imp_str = f"${self.impuesto_adicional:,}".replace(",", ".")
            output.append(f"  Impuesto Adicional: {imp_str}")
        
        output.append(f"  TOTAL: {total_str}")
        
        output.append("\n" + "=" * 80)
        
        return "\n".join(output)
