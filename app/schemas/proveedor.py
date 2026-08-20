from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from app.db.models import CategoriaProveedor, EstadoUsuario

class ProveedorCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    ruc_cedula: str = Field(..., min_length=5, max_length=20)
    nombre_comercial: str = Field(..., min_length=2, max_length=150)
    celular_whatsapp: str = Field(..., min_length=7, max_length=20)
    categoria: CategoriaProveedor
    especialidad: Optional[str] = None
    latitud: float
    longitud: float
    precio_consulta: Decimal = Field(..., ge=0)
    imagen_url: Optional[str] = None
    membresia_fija: Decimal = Field(default=Decimal("25.00"), ge=0)
    es_premium: bool = Field(default=False)
    link_tiktok: Optional[str] = None
    link_instagram: Optional[str] = None
    link_facebook: Optional[str] = None
    ciudad: Optional[str] = Field(default="Quito", min_length=2, max_length=100)
    sector: Optional[str] = None
    servicios_adicionales: Optional[List[dict]] = None

class ProveedorResponse(BaseModel):
    id: str
    usuario_id: str
    ruc_cedula: str
    nombre_comercial: str
    celular_whatsapp: Optional[str] = None
    categoria: CategoriaProveedor
    especialidad: Optional[str]
    latitud: float
    longitud: float
    precio_consulta: Decimal
    imagen_url: Optional[str]
    membresia_fija: Decimal
    es_premium: bool
    created_at: datetime
    email: Optional[EmailStr] = None
    estado: Optional[EstadoUsuario] = None
    link_tiktok: Optional[str] = None
    link_instagram: Optional[str] = None
    link_facebook: Optional[str] = None
    ciudad: Optional[str] = None
    sector: Optional[str] = None
    servicios_adicionales: Optional[List[dict]] = None

    class Config:
        from_attributes = True
        use_enum_values = True

class ProveedorRedesUpdate(BaseModel):
    link_tiktok: Optional[str] = None
    link_instagram: Optional[str] = None
    link_facebook: Optional[str] = None

class ProveedorAdminUpdate(BaseModel):
    nombre_comercial: Optional[str] = Field(None, min_length=2, max_length=150)
    ruc_cedula: Optional[str] = Field(None, min_length=5, max_length=20)
    celular_whatsapp: Optional[str] = Field(None, min_length=7, max_length=20)
    categoria: Optional[CategoriaProveedor] = None
    especialidad: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    precio_consulta: Optional[Decimal] = Field(None, ge=0)
    es_premium: Optional[bool] = None
    link_tiktok: Optional[str] = None
    link_instagram: Optional[str] = None
    link_facebook: Optional[str] = None
    ciudad: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    servicios_adicionales: Optional[List[dict]] = None


class ConfiguracionAgendaUpdate(BaseModel):
    horarios_disponibilidad: Optional[dict] = None
    duracion_turno: Optional[int] = Field(None, ge=10, le=120)
    respuesta_automatica: Optional[str] = Field(None, max_length=1000)


class ConfiguracionAgendaResponse(BaseModel):
    id: str
    proveedor_id: str
    horarios_disponibilidad: Optional[dict] = None
    duracion_turno: int
    respuesta_automatica: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CitaCreate(BaseModel):
    paciente_nombre: str = Field(..., min_length=2, max_length=150)
    fecha: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$") # YYYY-MM-DD
    hora_inicio: str = Field(..., pattern=r"^\d{2}:\d{2}$") # HH:MM
    hora_fin: str = Field(..., pattern=r"^\d{2}:\d{2}$") # HH:MM
    estado: str = Field(default="RESERVADA")


class CitaResponse(BaseModel):
    id: str
    proveedor_id: str
    paciente_id: Optional[str] = None
    paciente_nombre: str
    fecha: str
    hora_inicio: str
    hora_fin: str
    estado: str
    created_at: datetime

    class Config:
        from_attributes = True

