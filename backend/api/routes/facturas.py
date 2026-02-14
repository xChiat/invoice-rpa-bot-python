"""
Rutas de facturas: upload, listado, detalle, updates.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
import logging
import time

from backend.core.database import get_db
from backend.api.dependencies import get_current_user, get_current_empresa_id, get_client_ip
from backend.models.database.models import User, Factura, FacturaStatus, AuditLog
from backend.models.schemas.schemas import (
    FacturaResponse,
    FacturaListItem,
    FacturaStatusResponse,
    FacturaUpdate,
    MessageResponse
)
from backend.services.storage_service import storage_service
from backend.services.pdf_processor_service import pdf_processor_service
from backend.services.factura_extractor_service import factura_extractor_service
from backend.services.export_service import export_service

logger = logging.getLogger(__name__)
router = APIRouter()


async def process_factura_extraction(
    factura_id: int,
    pdf_url: str,
    db: Session
):
    """
    Tarea de background para procesar la extracción de una factura.
    
    Args:
        factura_id: ID de la factura a procesar
        pdf_url: URL del PDF a procesar
        db: Sesión de base de datos
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting extraction for factura {factura_id}")
        
        # Actualizar status a PROCESSING
        factura = db.query(Factura).filter(Factura.id == factura_id).first()
        if not factura:
            logger.error(f"Factura {factura_id} not found")
            return
        
        factura.status = FacturaStatus.PROCESSING
        db.commit()
        
        # Descargar PDF
        pdf_content = await storage_service.get_pdf(pdf_url)
        if not pdf_content:
            raise Exception("Could not download PDF")
        
        # Extraer texto del PDF
        extracted_text, tipo_factura_id = pdf_processor_service.extract_text(pdf_content)
        
        # Extraer campos de la factura
        campos = factura_extractor_service.extract_all(extracted_text)
        
        # Actualizar factura con datos extraídos
        factura.tipo_factura_id = tipo_factura_id
        factura.numero_factura = campos.get('numero_factura', 0)
        factura.fecha_emision = campos.get('fecha_emision')
        factura.empresa_emisora = campos.get('empresa_emisora', '')
        factura.rut_emisor = campos.get('rut_emisor', '')
        factura.domicilio_emisor = campos.get('domicilio_emisor', '')
        factura.empresa_destinataria = campos.get('empresa_destinataria', '')
        factura.rut_destinatario = campos.get('rut_destinatario', '')
        factura.domicilio_destinatario = campos.get('domicilio_destinatario', '')
        factura.monto_neto = campos.get('monto_neto', 0)
        factura.iva = campos.get('iva', 0)
        factura.total = campos.get('total', 0)
        factura.impuesto_adicional = campos.get('impuesto_adicional', 0)
        factura.raw_text = extracted_text[:5000]  # Guardar primeros 5000 chars
        factura.status = FacturaStatus.COMPLETED
        factura.completed_at = datetime.utcnow()
        
        # Calcular duración
        duration_ms = int((time.time() - start_time) * 1000)
        factura.extraction_duration_ms = duration_ms
        
        db.commit()
        
        logger.info(f"Extraction completed for factura {factura_id} in {duration_ms}ms")
        
    except Exception as e:
        logger.error(f"Error processing factura {factura_id}: {e}", exc_info=True)
        
        # Marcar como failed
        factura = db.query(Factura).filter(Factura.id == factura_id).first()
        if factura:
            factura.status = FacturaStatus.FAILED
            factura.validation_errors = str(e)
            db.commit()


@router.post("/upload", response_model=FacturaResponse, status_code=status.HTTP_201_CREATED)
async def upload_factura(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    client_ip: Optional[str] = Depends(get_client_ip)
):
    """
    Subir una factura PDF para procesamiento.
    
    Flujo:
    1. Validar archivo PDF
    2. Crear registro en DB con status PENDING
    3. Subir PDF a storage (Cloudinary/local)
    4. Encolar extracción en background
    5. Retornar ID y status
    """
    # Validar extensión
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Validar tamaño (en memoria antes de guardar)
    from backend.core.config import settings
    max_size = settings.max_upload_size_mb * 1024 * 1024
    
    try:
        # Crear registro en DB
        factura = Factura(
            empresa_id=current_user.empresa_id,
            uploaded_by=current_user.id,
            pdf_filename=file.filename,
            pdf_url="",  # Se actualizará después de subir
            status=FacturaStatus.PENDING
        )
        db.add(factura)
        db.commit()
        db.refresh(factura)
        
        logger.info(f"Created factura record {factura.id} for user {current_user.email}")
        
        # Subir PDF a storage
        pdf_url = await storage_service.save_pdf(file, current_user.empresa_id, factura.id)
        
        # Actualizar URL en DB
        factura.pdf_url = pdf_url
        db.commit()
        
        # Crear audit log
        audit = AuditLog(
            user_id=current_user.id,
            factura_id=factura.id,
            action="uploaded",
            details=f"Uploaded file: {file.filename}",
            ip_address=client_ip
        )
        db.add(audit)
        db.commit()
        
        # Encolar procesamiento en background
        background_tasks.add_task(
            process_factura_extraction,
            factura.id,
            pdf_url,
            db
        )
        
        logger.info(f"Factura {factura.id} queued for processing")
        
        return factura
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error uploading factura: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )


@router.get("/{factura_id}", response_model=FacturaResponse)
async def get_factura(
    factura_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener detalles de una factura específica.
    """
    factura = db.query(Factura).filter(
        Factura.id == factura_id,
        Factura.empresa_id == current_user.empresa_id  # Multi-tenant filter
    ).first()
    
    if not factura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura not found"
        )
    
    return factura


@router.get("/{factura_id}/status", response_model=FacturaStatusResponse)
async def get_factura_status(
    factura_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener el estado del procesamiento de una factura.
    Útil para polling desde el frontend.
    """
    factura = db.query(Factura).filter(
        Factura.id == factura_id,
        Factura.empresa_id == current_user.empresa_id
    ).first()
    
    if not factura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura not found"
        )
    
    # Calcular progreso
    progress_map = {
        FacturaStatus.PENDING: 10,
        FacturaStatus.PROCESSING: 50,
        FacturaStatus.COMPLETED: 100,
        FacturaStatus.FAILED: 0
    }
    
    progress = progress_map.get(factura.status, 0)
    
    # Mensaje descriptivo
    message_map = {
        FacturaStatus.PENDING: "Factura en cola de procesamiento",
        FacturaStatus.PROCESSING: "Extrayendo información de la factura...",
        FacturaStatus.COMPLETED: "Extracción completada exitosamente",
        FacturaStatus.FAILED: f"Error en la extracción: {factura.validation_errors or 'Unknown error'}"
    }
    
    return FacturaStatusResponse(
        id=factura.id,
        status=factura.status,
        progress=progress,
        message=message_map.get(factura.status, ""),
        data=factura if factura.status == FacturaStatus.COMPLETED else None
    )


@router.get("/", response_model=List[FacturaListItem])
async def list_facturas(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Listar facturas de la empresa del usuario actual.
    Soporta paginación y filtrado por status.
    """
    query = db.query(Factura).filter(
        Factura.empresa_id == current_user.empresa_id
    )
    
    # Filtrar por status si se proporciona
    if status_filter:
        try:
            status_enum = FacturaStatus(status_filter)
            query = query.filter(Factura.status == status_enum)
        except ValueError:
            pass  # Ignorar filtro inválido
    
    # Ordenar por más reciente primero
    query = query.order_by(desc(Factura.created_at))
    
    # Aplicar paginación
    facturas = query.offset(skip).limit(limit).all()
    
    return facturas


@router.patch("/{factura_id}", response_model=FacturaResponse)
async def update_factura(
    factura_id: int,
    updates: FacturaUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    client_ip: Optional[str] = Depends(get_client_ip)
):
    """
    Actualizar campos de una factura manualmente.
    Útil para corregir errores de extracción.
    """
    factura = db.query(Factura).filter(
        Factura.id == factura_id,
        Factura.empresa_id == current_user.empresa_id
    ).first()
    
    if not factura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura not found"
        )
    
    # Actualizar solo campos proporcionados
    update_data = updates.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(factura, field, value)
    
    factura.updated_at = datetime.utcnow()
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        factura_id=factura.id,
        action="updated",
        details=f"Updated fields: {', '.join(update_data.keys())}",
        ip_address=client_ip
    )
    db.add(audit)
    
    db.commit()
    db.refresh(factura)
    
    logger.info(f"Factura {factura_id} updated by user {current_user.email}")
    
    return factura


@router.delete("/{factura_id}", response_model=MessageResponse)
async def delete_factura(
    factura_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    client_ip: Optional[str] = Depends(get_client_ip)
):
    """
    Eliminar una factura (soft delete: marca como inactiva pero mantiene datos).
    Solo administradores pueden eliminar.
    """
    from backend.api.dependencies import require_admin
    await require_admin(current_user)
    
    factura = db.query(Factura).filter(
        Factura.id == factura_id,
        Factura.empresa_id == current_user.empresa_id
    ).first()
    
    if not factura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura not found"
        )
    
    # Eliminar PDF del storage
    await storage_service.delete_pdf(factura.pdf_url)
    
    # Eliminar registro de DB
    db.delete(factura)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        factura_id=None,  # Ya no existe
        action="deleted",
        details=f"Deleted factura {factura_id}: {factura.pdf_filename}",
        ip_address=client_ip
    )
    db.add(audit)
    
    db.commit()
    
    logger.info(f"Factura {factura_id} deleted by user {current_user.email}")
    
    return MessageResponse(message="Factura deleted successfully")


@router.get("/export/excel")
async def export_facturas_excel(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exportar facturas a Excel.
    Descarga todas las facturas de la empresa en formato XLSX.
    """
    from fastapi.responses import StreamingResponse
    
    query = db.query(Factura).filter(
        Factura.empresa_id == current_user.empresa_id
    )
    
    # Filtrar por status si se proporciona
    if status_filter:
        try:
            status_enum = FacturaStatus(status_filter)
            query = query.filter(Factura.status == status_enum)
        except ValueError:
            pass
    
    # Ordenar por fecha
    facturas = query.order_by(desc(Factura.created_at)).all()
    
    if not facturas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No invoices found to export"
        )
    
    # Generar Excel
    excel_file = export_service.export_facturas_to_excel(
        facturas,
        empresa_nombre=current_user.empresa.nombre
    )
    
    # Crear audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="exported",
        details=f"Exported {len(facturas)} facturas to Excel"
    )
    db.add(audit)
    db.commit()
    
    logger.info(f"Excel export generated for user {current_user.email}: {len(facturas)} facturas")
    
    # Nombre del archivo
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"facturas_{current_user.empresa.nombre}_{timestamp}.xlsx"
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
