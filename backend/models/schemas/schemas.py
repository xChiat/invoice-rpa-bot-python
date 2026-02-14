"""
Schemas Pydantic para validación de requests y serialización de responses.
Estos schemas se usan en los endpoints de FastAPI.
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


# ===== Enums =====

class UserRoleEnum(str, Enum):
    ADMIN = "admin"
    USER = "user"


class FacturaStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ===== Auth Schemas =====

class UserRegister(BaseModel):
    """Schema para registro de nuevo usuario y empresa"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = None
    empresa_nombre: str = Field(..., min_length=2, max_length=255)
    empresa_rut: str = Field(..., min_length=9, max_length=20)


class UserLogin(BaseModel):
    """Schema para login"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema para respuesta de autenticación"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema para datos decodificados del token"""
    user_id: int
    empresa_id: int
    role: UserRoleEnum


# ===== User Schemas =====

class UserBase(BaseModel):
    """Schema base de usuario"""
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema para crear usuario"""
    password: str = Field(..., min_length=8)
    role: UserRoleEnum = UserRoleEnum.USER
    empresa_id: int


class UserUpdate(BaseModel):
    """Schema para actualizar usuario"""
    full_name: Optional[str] = None
    role: Optional[UserRoleEnum] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema para respuesta de usuario"""
    id: int
    role: UserRoleEnum
    empresa_id: int
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ===== Empresa Schemas =====

class EmpresaBase(BaseModel):
    """Schema base de empresa"""
    nombre: str
    rut: str


class EmpresaCreate(EmpresaBase):
    """Schema para crear empresa"""
    plan: str = "free"


class EmpresaResponse(EmpresaBase):
    """Schema para respuesta de empresa"""
    id: int
    plan: str
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ===== Factura Schemas =====

class FacturaUpload(BaseModel):
    """Schema para metadata al subir factura"""
    # El archivo viene como UploadFile en FastAPI, no en el schema


class FacturaBase(BaseModel):
    """Schema base de factura con campos extraídos"""
    numero_factura: Optional[int] = None
    fecha_emision: Optional[date] = None
    empresa_emisora: Optional[str] = None
    rut_emisor: Optional[str] = None
    domicilio_emisor: Optional[str] = None
    empresa_destinataria: Optional[str] = None
    rut_destinatario: Optional[str] = None
    domicilio_destinatario: Optional[str] = None
    monto_neto: int = 0
    iva: int = 0
    total: int = 0
    impuesto_adicional: int = 0


class FacturaUpdate(BaseModel):
    """Schema para actualizar campos de factura manualmente"""
    numero_factura: Optional[int] = None
    fecha_emision: Optional[date] = None
    empresa_emisora: Optional[str] = None
    rut_emisor: Optional[str] = None
    domicilio_emisor: Optional[str] = None
    empresa_destinataria: Optional[str] = None
    rut_destinatario: Optional[str] = None
    domicilio_destinatario: Optional[str] = None
    monto_neto: Optional[int] = None
    iva: Optional[int] = None
    total: Optional[int] = None
    impuesto_adicional: Optional[int] = None


class FacturaResponse(FacturaBase):
    """Schema para respuesta completa de factura"""
    id: int
    empresa_id: int
    uploaded_by: int
    pdf_filename: str
    pdf_url: str
    status: FacturaStatusEnum
    tipo_factura_id: Optional[int] = None
    extraction_duration_ms: Optional[int] = None
    validation_errors: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class FacturaListItem(BaseModel):
    """Schema compacto para listado de facturas"""
    id: int
    numero_factura: Optional[int] = None
    fecha_emision: Optional[date] = None
    empresa_emisora: Optional[str] = None
    rut_emisor: Optional[str] = None
    total: int
    status: FacturaStatusEnum
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class FacturaStatusResponse(BaseModel):
    """Schema para respuesta de status de procesamiento"""
    id: int
    status: FacturaStatusEnum
    progress: int = Field(..., ge=0, le=100)  # Porcentaje de progreso
    message: str
    data: Optional[FacturaResponse] = None


# ===== Stats Schemas =====

class DashboardStats(BaseModel):
    """Schema para estadísticas del dashboard"""
    total_facturas: int
    facturas_mes_actual: int
    total_monto: int  # Suma de todos los totales
    tasa_exito_ocr: float  # Porcentaje de facturas completadas con éxito
    facturas_por_tipo: dict  # {"Escaneada": 10, "Digital": 15}
    facturas_por_mes: List[dict]  # [{"mes": "2026-01", "count": 25}, ...]


class TrendData(BaseModel):
    """Schema para datos de tendencias"""
    labels: List[str]
    datasets: List[dict]


# ===== Audit Log Schemas =====

class AuditLogResponse(BaseModel):
    """Schema para respuesta de log de auditoría"""
    id: int
    user_id: int
    factura_id: Optional[int] = None
    action: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ===== Generic Responses =====

class MessageResponse(BaseModel):
    """Schema genérico para mensajes"""
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Schema para respuestas de error"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
