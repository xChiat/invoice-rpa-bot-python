"""
Rutas de gestión de usuarios (solo admin).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from backend.core.database import get_db
from backend.api.dependencies import get_current_user, require_admin, get_client_ip
from backend.models.database.models import User, UserRole, AuditLog
from backend.models.schemas.schemas import (
    UserResponse,
    UserCreate,
    UserUpdate,
    MessageResponse
)
from backend.core.security import hash_password

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Listar todos los usuarios de la empresa.
    Solo accesible para administradores.
    """
    users = db.query(User).filter(
        User.empresa_id == current_user.empresa_id
    ).offset(skip).limit(limit).all()
    
    return users


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    client_ip: Optional[str] = Depends(get_client_ip)
):
    """
    Crear un nuevo usuario en la empresa.
    Solo accesible para administradores.
    """
    # Verificar que email no exista
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Verificar que el usuario admin solo puede crear usuarios en su empresa
    if user_data.empresa_id != current_user.empresa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create users for other companies"
        )
    
    try:
        # Crear usuario
        new_user = User(
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            full_name=user_data.full_name,
            role=user_data.role,
            empresa_id=user_data.empresa_id
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Audit log
        audit = AuditLog(
            user_id=current_user.id,
            action="user_created",
            details=f"Created user: {new_user.email} with role {new_user.role.value}",
            ip_address=client_ip
        )
        db.add(audit)
        db.commit()
        
        logger.info(f"User created: {new_user.email} by admin {current_user.email}")
        
        return new_user
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Obtener detalles de un usuario específico.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.empresa_id == current_user.empresa_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    updates: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    client_ip: Optional[str] = Depends(get_client_ip)
):
    """
    Actualizar información de un usuario.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.empresa_id == current_user.empresa_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # No permitir que un usuario se desactive a sí mismo
    if user_id == current_user.id and updates.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    # Actualizar campos
    update_data = updates.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="user_updated",
        details=f"Updated user {user.email}: {', '.join(update_data.keys())}",
        ip_address=client_ip
    )
    db.add(audit)
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"User {user_id} updated by admin {current_user.email}")
    
    return user


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    client_ip: Optional[str] = Depends(get_client_ip)
):
    """
    Eliminar un usuario (desactivar, no eliminar físicamente).
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.empresa_id == current_user.empresa_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # No permitir eliminar el propio usuario
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Desactivar usuario en vez de eliminar
    user.is_active = False
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="user_deleted",
        details=f"Deactivated user {user.email}",
        ip_address=client_ip
    )
    db.add(audit)
    
    db.commit()
    
    logger.info(f"User {user_id} deactivated by admin {current_user.email}")
    
    return MessageResponse(message="User deactivated successfully")
