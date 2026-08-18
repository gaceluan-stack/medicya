from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db import models
from app.schemas import paciente as paciente_schemas
from app.schemas import billing as billing_schemas
from app.api import deps

router = APIRouter(prefix="/pacientes", tags=["Pacientes"])

@router.get("/me", response_model=paciente_schemas.PacienteResponse)
def get_paciente_profile(
    current_user: models.UsuarioSistema = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna el perfil del paciente actualmente autenticado.
    """
    if current_user.rol != models.RolUsuario.PACIENTE:
        raise HTTPException(
            status_code=403,
            detail="Este endpoint solo está disponible para pacientes"
        )
        
    paciente = db.query(models.Paciente).filter(
        models.Paciente.usuario_id == current_user.id
    ).first()
    
    if not paciente:
        raise HTTPException(
            status_code=404,
            detail="Perfil de paciente no encontrado"
        )
        
    return paciente

@router.get("/me/cupones", response_model=List[billing_schemas.CuponResponse])
def get_paciente_cupones(
    current_user: models.UsuarioSistema = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna todos los cupones activos o redimidos del paciente.
    """
    if current_user.rol != models.RolUsuario.PACIENTE:
        raise HTTPException(
            status_code=403,
            detail="Este endpoint solo está disponible para pacientes"
        )
        
    paciente = db.query(models.Paciente).filter(
        models.Paciente.usuario_id == current_user.id
    ).first()
    
    if not paciente:
        raise HTTPException(
            status_code=404,
            detail="Perfil de paciente no encontrado"
        )
        
    cupones = db.query(models.Cupon).filter(
        models.Cupon.paciente_id == paciente.id
    ).order_by(models.Cupon.created_at.desc()).all()
    
    return cupones

@router.post("/solicitar-publicidad")
def solicitar_publicidad_paciente(
    pub_in: billing_schemas.SolicitudPublicidadCreate,
    current_user: models.UsuarioSistema = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permite a los pacientes (clientes gratuitos) solicitar publicidad para sus propios negocios.
    """
    if current_user.rol != models.RolUsuario.PACIENTE:
        raise HTTPException(
            status_code=403,
            detail="Este endpoint solo está disponible para pacientes"
        )
        
    nueva_solicitud = models.SolicitudPublicidad(
        usuario_id=current_user.id,
        plataformas=pub_in.plataformas,
        cantidad_vistas=pub_in.cantidad_vistas,
        precio=pub_in.precio,
        estado="PENDIENTE",
        veces_publicado=0
    )
    db.add(nueva_solicitud)
    db.commit()
    
    return {"message": "Tu solicitud de publicidad ha sido registrada con éxito. La administración te contactará al WhatsApp para coordinar el pago.", "solicitud_id": nueva_solicitud.id}

@router.put("/me/perfil", response_model=paciente_schemas.PacienteResponse)
def update_paciente_profile(
    profile_in: paciente_schemas.PacienteProfileUpdate,
    current_user: models.UsuarioSistema = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permite al paciente actualizar sus datos personales y de redes sociales.
    """
    if current_user.rol != models.RolUsuario.PACIENTE:
        raise HTTPException(
            status_code=403,
            detail="Este endpoint solo está disponible para pacientes"
        )
        
    paciente = db.query(models.Paciente).filter(
        models.Paciente.usuario_id == current_user.id
    ).first()
    
    if not paciente:
        raise HTTPException(
            status_code=404,
            detail="Perfil de paciente no encontrado"
        )
        
    if profile_in.nombres is not None:
        paciente.nombres = profile_in.nombres
    if profile_in.apellidos is not None:
        paciente.apellidos = profile_in.apellidos
    if profile_in.celular_whatsapp is not None:
        paciente.celular_whatsapp = profile_in.celular_whatsapp
    if profile_in.link_tiktok is not None:
        paciente.link_tiktok = profile_in.link_tiktok
    if profile_in.link_instagram is not None:
        paciente.link_instagram = profile_in.link_instagram
    if profile_in.link_facebook is not None:
        paciente.link_facebook = profile_in.link_facebook
        
    db.commit()
    db.refresh(paciente)
    return paciente
