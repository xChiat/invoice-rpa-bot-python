"""
Dependencias de FastAPI para inyección en endpoints.
Incluye autenticación, obtención de usuario actual, verificación de roles, etc.
"""
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional

from backend.core.database import get_db
from backend.core.security import decode_token
from backend.models.database.models import User, UserRole
from backend.models.schemas.schemas import TokenData


# OAuth2 scheme para extraer token del header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency para obtener el usuario actual desde el token JWT.
    
    Args:
        token: Token JWT del header Authorization
        db: Sesión de base de datos
        
    Returns:
        Usuario autenticado
        
    Raises:
        HTTPException 401: Si el token es inválido o el usuario no existe
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Decodificar token
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    # Extraer datos del token
    user_id: int = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
    
    # Buscar usuario en base de datos
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    # Verificar que el usuario está activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency para verificar que el usuario está activo.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency para endpoints que requieren rol de administrador.
    
    Args:
        current_user: Usuario actual
        
    Returns:
        Usuario con rol admin
        
    Raises:
        HTTPException 403: Si el usuario no es administrador
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required"
        )
    return current_user


async def get_current_empresa_id(
    current_user: User = Depends(get_current_user)
) -> int:
    """
    Dependency para obtener el ID de la empresa del usuario actual.
    Útil para garantizar aislamiento multi-tenant.
    
    Args:
        current_user: Usuario actual
        
    Returns:
        ID de la empresa del usuario
    """
    return current_user.empresa_id


def verify_empresa_access(
    factura_empresa_id: int,
    current_user: User = Depends(get_current_user)
) -> bool:
    """
    Verificar que el usuario tiene acceso a recursos de una empresa específica.
    
    Args:
        factura_empresa_id: ID de la empresa del recurso
        current_user: Usuario actual
        
    Returns:
        True si tiene acceso
        
    Raises:
        HTTPException 403: Si el usuario no tiene acceso
    """
    if factura_empresa_id != current_user.empresa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: resource belongs to another company"
        )
    return True


async def get_client_ip(
    x_forwarded_for: Optional[str] = Header(None),
    x_real_ip: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Dependency para obtener la IP del cliente.
    Útil para audit logs.
    
    Args:
        x_forwarded_for: Header X-Forwarded-For (proxies)
        x_real_ip: Header X-Real-IP (nginx)
        
    Returns:
        IP del cliente o None
    """
    if x_forwarded_for:
        # X-Forwarded-For puede tener múltiples IPs, tomar la primera
        return x_forwarded_for.split(",")[0].strip()
    return x_real_ip
