from pathlib import Path
from extraction import extract_text_from_pdf
from ai_extraction import FacturaExtractor


def main():
    """
    Función principal que procesa todos los PDFs en data/input/
    """
    # Configurar rutas
    base_dir = Path(__file__).parent.parent  
    input_dir = base_dir / "data" / "input"
    
    # Verificar que el directorio de entrada existe
    if not input_dir.exists():
        print(f"Error: El directorio {input_dir} no existe")
        return
    
    # Obtener lista de archivos PDF en el directorio de entrada
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No se encontraron archivos PDF en {input_dir}")
        return
    
    print(f"Se encontraron {len(pdf_files)} archivo(s) PDF\n")
    
    # Inicializar extractor inteligente
    extractor = FacturaExtractor()
    
    # Procesar cada PDF
    for pdf_path in pdf_files:
        print("=" * 80)
        print(f"Procesando: {pdf_path.name}")
        print("=" * 80)
        
        try:
            # Extraer texto del PDF
            extracted_text = extract_text_from_pdf(str(pdf_path))
            
            # Mostrar el texto extraído
            print(extracted_text)
            print()
            
            # Extraer campos inteligentemente
            factura_datos = extractor.extract_all(extracted_text)
            
            # Mostrar datos extraídos
            print(extractor.format_factura(factura_datos))
            print("\n" + "=" * 80 + "\n")
            
        except Exception as e:
            print(f"✗ Error al procesar {pdf_path.name}: {e}\n")


if __name__ == "__main__":
    main()
