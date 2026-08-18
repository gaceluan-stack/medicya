from pydantic import BaseModel, Field
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from app.db.models import EstadoFactura, EstadoLeadCrm, EstadoCupon

class FacturaResponse(BaseModel):
    id: str
    proveedor_id: str
    fecha_emision: date
    fecha_vencimiento: date
    monto_fijo: Decimal
    monto_clics: Decimal
    monto_total: Decimal
    estado: EstadoFactura
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True

class ProspectoInfo(BaseModel):
    id: str # Clic ID para el CRM
    nombres: str
    apellidos: str
    cedula: str
    celular_whatsapp: str
    email: str
    estado_lead: EstadoLeadCrm
    fecha_contacto: datetime
    link_tiktok: Optional[str] = None
    link_instagram: Optional[str] = None
    link_facebook: Optional[str] = None

    class Config:
        from_attributes = True
        use_enum_values = True

class LeadStatusUpdate(BaseModel):
    estado_lead: EstadoLeadCrm

class MetricasProveedor(BaseModel):
    clics_recibidos: int
    prospectos_generados: int
    balance_acumulado: Decimal
    membresia_fija: Decimal
    estado_cuenta: str
    lista_prospectos: List[ProspectoInfo]
    es_premium: Optional[bool] = False
    link_tiktok: Optional[str] = None
    link_instagram: Optional[str] = None
    link_facebook: Optional[str] = None

class ReporteAtribucion(BaseModel):
    origen: str
    cantidad: int
    porcentaje: float

# --- Nuevos Esquemas para Campañas, Cupones y Reseñas ---

class CampanaCreate(BaseModel):
    codigo: str = Field(..., min_length=3, max_length=50)
    monto: Decimal = Field(default=Decimal("5.00"), ge=1.00)
    limite_usos: Optional[int] = Field(default=100, ge=1)

class CampanaResponse(BaseModel):
    id: str
    proveedor_id: str
    codigo: str
    monto: Decimal
    limite_usos: int
    usos_actuales: int
    created_at: datetime

    class Config:
        from_attributes = True

class CuponResponse(BaseModel):
    id: str
    paciente_id: str
    codigo: str
    monto: Decimal
    estado: EstadoCupon
    proveedor_redencion_id: Optional[str] = None
    campana_id: Optional[str] = None
    fecha_redencion: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True

class ResenaCreate(BaseModel):
    calificacion: int = Field(..., ge=1, le=5)
    comentario: Optional[str] = Field(None, max_length=500)

class ResenaResponse(BaseModel):
    id: str
    proveedor_id: str
    paciente_id: str
    paciente_nombre: str
    calificacion: int
    comentario: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

from app.schemas.publicidad import SolicitudPublicidadCreate, SolicitudPublicidadResponse
