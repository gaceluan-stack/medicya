from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from decimal import Decimal
from typing import Optional
import re
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

    @field_validator("celular_whatsapp")
    @classmethod
    def validate_celular(cls, v):
        # Eliminar cualquier caracter no numérico excepto el signo +
        cleaned = re.sub(r"[^\d\+]", "", v)
        # Expresión regular para Ecuador: 
        # - 09 seguido de 8 dígitos (10 en total)
        # - +5939 seguido de 8 dígitos (13 en total)
        # - 5939 seguido de 8 dígitos (12 en total)
        pattern = r"^(09\d{8}|\+5939\d{8}|5939\d{8})$"
        if not re.match(pattern, cleaned):
            raise ValueError(
                "El número de celular debe ser un celular real (ej: 0998765432 o +593998765432)"
            )
        return cleaned

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
