"""
Rutas de estadísticas y dashboard.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from typing import Dict, List
import logging

from backend.core.database import get_db
from backend.api.dependencies import get_current_user, get_current_empresa_id
from backend.models.database.models import User, Factura, FacturaStatus, TipoFactura
from backend.models.schemas.schemas import DashboardStats

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas del dashboard para la empresa del usuario.
    
    Incluye:
    - Total de facturas
    - Facturas del mes actual
    - Suma total de montos
    - Tasa de éxito OCR
    - Distribución por tipo (Escaneada/Digital)
    - Tendencia por mes
    """
    empresa_id = current_user.empresa_id
    
    # Total de facturas
    total_facturas = db.query(Factura).filter(
        Factura.empresa_id == empresa_id
    ).count()
    
    # Facturas del mes actual
    now = datetime.utcnow()
    first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    facturas_mes_actual = db.query(Factura).filter(
        Factura.empresa_id == empresa_id,
        Factura.created_at >= first_day_of_month
    ).count()
    
    # Suma total de montos (solo facturas completadas)
    total_monto = db.query(func.sum(Factura.total)).filter(
        Factura.empresa_id == empresa_id,
        Factura.status == FacturaStatus.COMPLETED
    ).scalar() or 0
    
    # Tasa de éxito OCR (facturas completadas vs total)
    completadas = db.query(Factura).filter(
        Factura.empresa_id == empresa_id,
        Factura.status == FacturaStatus.COMPLETED
    ).count()
    
    tasa_exito = (completadas / total_facturas * 100) if total_facturas > 0 else 0.0
    
    # Distribución por tipo
    facturas_por_tipo = {}
    tipos_query = db.query(
        TipoFactura.tipo,
        func.count(Factura.id).label('count')
    ).join(
        Factura, Factura.tipo_factura_id == TipoFactura.id
    ).filter(
        Factura.empresa_id == empresa_id
    ).group_by(TipoFactura.tipo).all()
    
    for tipo, count in tipos_query:
        facturas_por_tipo[tipo] = count
    
    # Tendencia por mes (últimos 6 meses)
    six_months_ago = now - timedelta(days=180)
    
    facturas_por_mes_query = db.query(
        extract('year', Factura.created_at).label('year'),
        extract('month', Factura.created_at).label('month'),
        func.count(Factura.id).label('count')
    ).filter(
        Factura.empresa_id == empresa_id,
        Factura.created_at >= six_months_ago
    ).group_by('year', 'month').order_by('year', 'month').all()
    
    facturas_por_mes = []
    for year, month, count in facturas_por_mes_query:
        facturas_por_mes.append({
            'mes': f"{int(year)}-{str(int(month)).zfill(2)}",
            'count': count
        })
    
    logger.info(f"Dashboard stats generated for empresa {empresa_id}")
    
    return DashboardStats(
        total_facturas=total_facturas,
        facturas_mes_actual=facturas_mes_actual,
        total_monto=int(total_monto),
        tasa_exito_ocr=round(tasa_exito, 2),
        facturas_por_tipo=facturas_por_tipo,
        facturas_por_mes=facturas_por_mes
    )


@router.get("/top-emisores")
async def get_top_emisores(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener los top N emisores por monto total.
    """
    empresa_id = current_user.empresa_id
    
    top_emisores = db.query(
        Factura.empresa_emisora,
        Factura.rut_emisor,
        func.count(Factura.id).label('cantidad'),
        func.sum(Factura.total).label('monto_total')
    ).filter(
        Factura.empresa_id == empresa_id,
        Factura.status == FacturaStatus.COMPLETED,
        Factura.empresa_emisora != '',
        Factura.empresa_emisora.isnot(None)
    ).group_by(
        Factura.empresa_emisora,
        Factura.rut_emisor
    ).order_by(
        func.sum(Factura.total).desc()
    ).limit(limit).all()
    
    result = []
    for empresa, rut, cantidad, monto in top_emisores:
        result.append({
            'empresa': empresa,
            'rut': rut,
            'cantidad_facturas': cantidad,
            'monto_total': int(monto or 0)
        })
    
    return result


@router.get("/resumen-mensual/{year}/{month}")
async def get_resumen_mensual(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener resumen completo de un mes específico.
    """
    empresa_id = current_user.empresa_id
    
    # Calcular rango de fechas
    from datetime import date
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1)
    else:
        last_day = date(year, month + 1, 1)
    
    # Facturas del mes
    facturas_mes = db.query(Factura).filter(
        Factura.empresa_id == empresa_id,
        Factura.created_at >= first_day,
        Factura.created_at < last_day
    ).all()
    
    # Calcular estadísticas
    total_facturas = len(facturas_mes)
    completadas = sum(1 for f in facturas_mes if f.status == FacturaStatus.COMPLETED)
    fallidas = sum(1 for f in facturas_mes if f.status == FacturaStatus.FAILED)
    
    monto_total = sum(f.total for f in facturas_mes if f.status == FacturaStatus.COMPLETED)
    monto_neto = sum(f.monto_neto for f in facturas_mes if f.status == FacturaStatus.COMPLETED)
    iva_total = sum(f.iva for f in facturas_mes if f.status == FacturaStatus.COMPLETED)
    
    return {
        'periodo': f"{year}-{str(month).zfill(2)}",
        'total_facturas': total_facturas,
        'completadas': completadas,
        'fallidas': fallidas,
        'pendientes': total_facturas - completadas - fallidas,
        'monto_total': int(monto_total),
        'monto_neto': int(monto_neto),
        'iva_total': int(iva_total)
    }
