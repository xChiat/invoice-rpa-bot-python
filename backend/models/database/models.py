"""
Modelos SQLAlchemy para la base de datos.
Representan las tablas en PostgreSQL.
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
import enum

from backend.core.database import Base


class UserRole(str, enum.Enum):
    """Roles de usuario en el sistema"""
    ADMIN = "admin"
    USER = "user"


class FacturaStatus(str, enum.Enum):
    """Estados del procesamiento de facturas"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Empresa(Base):
    """
    Tabla de empresas para multi-tenancy.
    Cada empresa tiene sus propios usuarios y facturas aislados.
    """
    __tablename__ = "empresas"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False, index=True)
    rut = Column(String(20), unique=True, nullable=False, index=True)
    plan = Column(String(50), default="free")  # free, premium, enterprise
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="empresa", cascade="all, delete-orphan")
    facturas = relationship("Factura", back_populates="empresa", cascade="all, delete-orphan")


class User(Base):
    """
    Tabla de usuarios del sistema.
    Cada usuario pertenece a una empresa y tiene un rol.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    empresa = relationship("Empresa", back_populates="users")
    facturas_uploaded = relationship("Factura", back_populates="uploaded_by_user", foreign_keys="Factura.uploaded_by")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


class TipoFactura(Base):
    """
    Tabla de tipos de factura (seed data).
    1 = Escaneada (OCR), 2 = Digital (texto extraíble)
    """
    __tablename__ = "tipos_factura"
    
    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(50), unique=True, nullable=False)
    descripcion = Column(String(255), nullable=True)
    
    # Relationships
    facturas = relationship("Factura", back_populates="tipo_factura")


class Factura(Base):
    """
    Tabla principal de facturas extraídas.
    Contiene todos los campos extraídos del PDF más metadata.
    """
    __tablename__ = "facturas"
    
    # Primary key y metadata
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Archivo original
    pdf_filename = Column(String(255), nullable=False)
    pdf_url = Column(String(500), nullable=False)  # URL en Cloudinary
    
    # Estado del procesamiento
    status = Column(Enum(FacturaStatus), default=FacturaStatus.PENDING, nullable=False, index=True)
    tipo_factura_id = Column(Integer, ForeignKey("tipos_factura.id"), nullable=True)
    
    # Campos extraídos de la factura
    numero_factura = Column(Integer, nullable=True, index=True)
    fecha_emision = Column(Date, nullable=True, index=True)
    
    # Empresa emisora
    empresa_emisora = Column(String(255), nullable=True)
    rut_emisor = Column(String(20), nullable=True, index=True)
    domicilio_emisor = Column(Text, nullable=True)
    
    # Empresa destinataria
    empresa_destinataria = Column(String(255), nullable=True)
    rut_destinatario = Column(String(20), nullable=True, index=True)
    domicilio_destinatario = Column(Text, nullable=True)
    
    # Montos (almacenados como enteros, sin decimales para facturas chilenas)
    monto_neto = Column(Integer, default=0, nullable=False)
    iva = Column(Integer, default=0, nullable=False)
    total = Column(Integer, default=0, nullable=False, index=True)
    impuesto_adicional = Column(Integer, default=0, nullable=False)
    
    # Metadata del procesamiento
    extraction_duration_ms = Column(Integer, nullable=True)  # Tiempo de extracción en milisegundos
    validation_errors = Column(Text, nullable=True)  # JSON con errores de validación
    raw_text = Column(Text, nullable=True)  # Texto completo extraído (para debugging)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)  # Cuando terminó el procesamiento
    
    # Relationships
    empresa = relationship("Empresa", back_populates="facturas")
    uploaded_by_user = relationship("User", back_populates="facturas_uploaded", foreign_keys=[uploaded_by])
    tipo_factura = relationship("TipoFactura", back_populates="facturas")
    audit_logs = relationship("AuditLog", back_populates="factura", cascade="all, delete-orphan")


class AuditLog(Base):
    """
    Tabla de auditoría para tracking de acciones.
    Registra quién hizo qué y cuándo.
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    factura_id = Column(Integer, ForeignKey("facturas.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # uploaded, extracted, validated, exported
    details = Column(Text, nullable=True)  # JSON con detalles adicionales
    ip_address = Column(String(45), nullable=True)  # IPv4 o IPv6
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    factura = relationship("Factura", back_populates="audit_logs")
