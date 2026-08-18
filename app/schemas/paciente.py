from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from app.db.models import CanalAtribucion

class PacienteCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    nombres: str = Field(..., min_length=2, max_length=100)
    apellidos: str = Field(..., min_length=2, max_length=100)
    cedula: str = Field(..., min_length=5, max_length=20)
    celular_whatsapp: str = Field(..., min_length=7, max_length=20)
    origen_informacion: CanalAtribucion
    referido_por_id: Optional[str] = None # Añadido para el programa de referidos
    verification_code: Optional[str] = None
    link_tiktok: Optional[str] = None
    link_instagram: Optional[str] = None
    link_facebook: Optional[str] = None

class PacienteResponse(BaseModel):
    id: str
    usuario_id: str
    email: Optional[str] = None
    nombres: str
    apellidos: str
    cedula: str
    celular_whatsapp: str
    origen_informacion: CanalAtribucion
    cupon_descuento: Decimal
    cupon_usado: bool
    referido_por_id: Optional[str] = None
    link_tiktok: Optional[str] = None
    link_instagram: Optional[str] = None
    link_facebook: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True

class PacienteProfileUpdate(BaseModel):
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    celular_whatsapp: Optional[str] = None
    link_tiktok: Optional[str] = None
    link_instagram: Optional[str] = None
    link_facebook: Optional[str] = None
