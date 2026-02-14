#!/usr/bin/env python3
"""
Script de inicialización del proyecto Invoice RPA Bot.
Ejecuta todos los pasos necesarios para configurar el backend.
"""
import sys
import subprocess
import os
from pathlib import Path

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def run_command(command, description):
    """Ejecutar un comando y mostrar resultado"""
    print(f"\n{Colors.BOLD}→ {description}...{Colors.END}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print_success(f"{description} completado")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"{description} falló")
        print(f"Error: {e.stderr}")
        return False

def check_dependencies():
    """Verificar que dependencias estén instaladas"""
    print_header("Verificando Dependencias")
    
    dependencies = {
        'python': 'python --version',
        'pip': 'pip --version',
        'tesseract': 'tesseract --version',
        'postgres': 'psql --version'
    }
    
    all_ok = True
    for name, cmd in dependencies.items():
        try:
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
            print_success(f"{name.capitalize()} instalado")
        except subprocess.CalledProcessError:
            print_warning(f"{name.capitalize()} no encontrado")
            if name == 'tesseract':
                print("  → Descargar: https://github.com/UB-Mannheim/tesseract/wiki")
            elif name == 'postgres':
                print("  → Opcional: Puedes usar Railway/Render managed database")
            else:
                all_ok = False
    
    return all_ok

def check_env_file():
    """Verificar que .env exista"""
    print_header("Verificando Configuración")
    
    env_path = Path('.env')
    if not env_path.exists():
        print_warning(".env no encontrado")
        
        # Copiar ejemplo
        example_path = Path('.env.example')
        if example_path.exists():
            with open(example_path, 'r') as f:
                content = f.read()
            
            with open(env_path, 'w') as f:
                f.write(content)
            
            print_success(".env creado desde .env.example")
            print(f"\n{Colors.YELLOW}IMPORTANTE: Edita .env y configura:{Colors.END}")
            print("  - DATABASE_URL")
            print("  - SECRET_KEY (generar aleatorio)")
            print("  - CLOUDINARY_* (credenciales)")
            
            return False
        else:
            print_error(".env.example no encontrado")
            return False
    else:
        print_success(".env existe")
        
        # Verificar variables críticas
        with open(env_path, 'r') as f:
            content = f.read()
        
        required = ['DATABASE_URL', 'SECRET_KEY']
        missing = [var for var in required if var not in content or f'{var}=' not in content]
        
        if missing:
            print_warning(f"Variables faltantes en .env: {', '.join(missing)}")
            return False
        
        return True

def install_dependencies():
    """Instalar dependencias Python"""
    print_header("Instalando Dependencias Python")
    
    requirements = Path('backend/requirements.txt')
    if not requirements.exists():
        print_error("backend/requirements.txt no encontrado")
        return False
    
    return run_command(
        'pip install -r backend/requirements.txt',
        'Instalación de dependencias'
    )

def run_migrations():
    """Ejecutar migraciones de base de datos"""
    print_header("Configurando Base de Datos")
    
    # Verificar si Alembic está inicializado
    if not Path('backend/alembic/versions').exists():
        os.makedirs('backend/alembic/versions', exist_ok=True)
        print_success("Directorio de migraciones creado")
    
    # Crear migración inicial si no existe
    versions = list(Path('backend/alembic/versions').glob('*.py'))
    if not versions:
        print("Creando migración inicial...")
        run_command(
            'alembic revision --autogenerate -m "Initial migration"',
            'Generación de migración inicial'
        )
    
    # Aplicar migraciones
    return run_command(
        'alembic upgrade head',
        'Aplicación de migraciones'
    )

def seed_database():
    """Poblar datos iniciales"""
    print_header("Poblando Datos Iniciales")
    
    return run_command(
        'python -m backend.scripts.seed_data',
        'Seed de datos iniciales'
    )

def main():
    """Función principal"""
    print(f"\n{Colors.BOLD}{Colors.GREEN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          🚀 Invoice RPA Bot - Inicialización 🚀          ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(Colors.END)
    
    # Verificar que estamos en el directorio correcto
    if not Path('backend').exists():
        print_error("Ejecuta este script desde la raíz del proyecto")
        sys.exit(1)
    
    # Paso 1: Verificar dependencias
    if not check_dependencies():
        print_warning("\nInstalación incompleta. Instala las dependencias faltantes.")
        sys.exit(1)
    
    # Paso 2: Verificar .env
    env_ok = check_env_file()
    if not env_ok:
        print(f"\n{Colors.YELLOW}Configura .env antes de continuar.{Colors.END}")
        print("Ejecuta nuevamente este script después de configurar.")
        sys.exit(0)
    
    # Paso 3: Instalar dependencias Python
    if not install_dependencies():
        print_error("Error instalando dependencias")
        sys.exit(1)
    
    # Paso 4: Migraciones
    if not run_migrations():
        print_error("Error ejecutando migraciones")
        print_warning("Verifica que DATABASE_URL en .env sea correcto")
        sys.exit(1)
    
    # Paso 5: Seed
    if not seed_database():
        print_warning("Error en seed (puede ser normal si ya existen datos)")
    
    # Resumen final
    print_header("✨ Inicialización Completada ✨")
    print(f"{Colors.GREEN}El backend está listo para usar!{Colors.END}\n")
    print(f"{Colors.BOLD}Próximos pasos:{Colors.END}")
    print("  1. Revisar .env tiene todas las variables configuradas")
    print("  2. Iniciar servidor: uvicorn backend.api.main:app --reload")
    print("  3. Visitar docs: http://localhost:8000/api/docs")
    print("  4. Registrar primera empresa: POST /api/auth/register")
    print(f"\n{Colors.BLUE}Ver BACKEND_SETUP.md para más detalles.{Colors.END}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Inicialización cancelada por el usuario.{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Error inesperado: {e}{Colors.END}")
        sys.exit(1)
