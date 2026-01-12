import os
from pathlib import Path
from extraction import extract_text_from_pdf


def main():
    """
    Función principal que procesa todos los PDFs en data/input/
    """
    # Configurar rutas
    base_dir = Path(__file__).parent.parent  
    input_dir = base_dir / "data" / "input"
    output_dir = base_dir / "data" / "output"
    
    # Crear directorio de salida si no existe
    output_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    # Procesar cada PDF
    for pdf_path in pdf_files:
        print("=" * 80)
        print(f"Procesando: {pdf_path.name}")
        print("=" * 80)
        
        try:
            # Extraer texto del PDF
            extracted_text = extract_text_from_pdf(str(pdf_path))
            
            # Mostrar el texto en la terminal
            print("\n--- TEXTO EXTRAÍDO ---\n")
            print(extracted_text)
            print("\n" + "=" * 80 + "\n")
            
        except Exception as e:
            print(f"✗ Error al procesar {pdf_path.name}: {e}\n")


if __name__ == "__main__":
    main()
