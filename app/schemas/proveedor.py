from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from app.db.models import CategoriaProveedor, EstadoUsuario

class ProveedorCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    ruc_cedula: str = Field(..., min_length=5, max_length=20)
    nombre_comercial: str = Field(..., min_length=2, max_length=150)
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

class ProveedorResponse(BaseModel):
    id: str
    usuario_id: str
    ruc_cedula: str
    nombre_comercial: str
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

    class Config:
        from_attributes = True
        use_enum_values = True

class ProveedorRedesUpdate(BaseModel):
    link_tiktok: Optional[str] = None
    link_instagram: Optional[str] = None
    link_facebook: Optional[str] = None
