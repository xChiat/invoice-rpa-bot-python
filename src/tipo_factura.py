from dataclasses import dataclass

@dataclass
class TipoFactura:
    """
    Clase que representa el tipo de factura, 
    clasifica las facturas entre escaneadas o digitales.
    
    Attributes:
        id_tipo (int): Identificador del tipo de factura.
        tipo_factura (str): Descripción del tipo de factura.
    """
    id_tipo: int = 0
    tipo_factura: str = ""