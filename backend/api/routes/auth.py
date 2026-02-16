"""
Rutas de autenticación: registro, login, refresh token.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from backend.core.database import get_db
from backend.api.dependencies import get_current_user
from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from backend.models.database.models import User, Empresa
from backend.models.schemas.schemas import (
    UserRegister,
    UserLogin,
    Token,
    MessageResponse,
    UserResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Registrar nuevo usuario y empresa.
    Crea una nueva empresa y un usuario administrador para esa empresa.
    
    Flujo:
    1. Verificar que email no exista
    2. Verificar que RUT de empresa no exista
    3. Crear empresa
    4. Crear usuario admin
    5. Retornar tokens
    """
    logger.info(f"Attempting to register new user/company")
    logger.info(f"Email: {user_data.email}")
    logger.info(f"Full name: {user_data.full_name}")
    logger.info(f"Company name: {user_data.empresa_nombre}")
    logger.info(f"Company RUT: {user_data.empresa_rut}")
    
    # Verificar si email ya existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        logger.warning(f"Registration failed: Email {user_data.email} already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Verificar si empresa ya existe
    existing_empresa = db.query(Empresa).filter(Empresa.rut == user_data.empresa_rut).first()
    if existing_empresa:
        logger.warning(f"Registration failed: Company RUT {user_data.empresa_rut} already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company RUT already registered"
        )
    
    try:
        # Crear empresa
        logger.info("Creating new company...")
        empresa = Empresa(
            nombre=user_data.empresa_nombre,
            rut=user_data.empresa_rut,
            plan="free"
        )
        db.add(empresa)
        db.flush()  # Para obtener el ID sin hacer commit
        logger.info(f"Company created with ID: {empresa.id}")
        
        # Crear usuario administrador
        logger.info("Creating admin user...")
        user = User(
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            full_name=user_data.full_name,
            role="admin",
            empresa_id=empresa.id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"User created with ID: {user.id}")
        
        logger.info(f"✓ Registration successful: {user.email} (empresa_id: {empresa.id})")
        
        # Crear tokens
        logger.info("Generating authentication tokens...")
        token_data = {
            "user_id": user.id,
            "empresa_id": user.empresa_id,
            "role": user.role.value
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        logger.info("Registration completed successfully")
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
        
    except HTTPException:
        # Re-lanzar HTTPException sin modificar
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"✗ Database error during registration: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user account: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Iniciar sesión con email y contraseña.
    Retorna access token y refresh token.
    """
    # Buscar usuario por email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verificar contraseña
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verificar que usuario está activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    logger.info(f"User logged in: {user.email}")
    
    # Crear tokens
    token_data = {
        "user_id": user.id,
        "empresa_id": user.empresa_id,
        "role": user.role.value
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refrescar access token usando un refresh token válido.
    """
    # Decodificar refresh token
    payload = decode_token(refresh_token)
    
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Verificar que usuario existe y está activo
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Crear nuevo access token
    token_data = {
        "user_id": user.id,
        "empresa_id": user.empresa_id,
        "role": user.role.value
    }
    new_access_token = create_access_token(token_data)
    
    return Token(
        access_token=new_access_token,
        refresh_token=refresh_token,  # Mantener el mismo refresh token
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener información del usuario autenticado actual.
    """
    return current_user
