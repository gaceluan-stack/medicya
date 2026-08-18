from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from app.db.models import RolUsuario, EstadoUsuario

class UsuarioBase(BaseModel):
    email: EmailStr
    rol: RolUsuario
    estado: Optional[EstadoUsuario] = EstadoUsuario.ACTIVO

class UsuarioCreate(UsuarioBase):
    password: Optional[str] = None

class UsuarioResponse(BaseModel):
    id: str
    email: EmailStr
    rol: RolUsuario
    estado: EstadoUsuario
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True
