from pydantic import BaseModel, ConfigDict
from datetime import datetime
from decimal import Decimal
from typing import Optional

class SolicitudPublicidadCreate(BaseModel):
    plataformas: str  # "Instagram, Facebook, TikTok"
    cantidad_vistas: int  # 500, 1000, 2000
    precio: Decimal  # 10.00, 20.00, 25.00

class SolicitudPublicidadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    usuario_id: str
    plataformas: str
    cantidad_vistas: int
    precio: Decimal
    estado: str
    veces_publicado: int
    created_at: datetime
    email: Optional[str] = None
    rol: Optional[str] = None
