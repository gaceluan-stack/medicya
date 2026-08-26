import uuid
import math
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from app.schemas import proveedor as proveedor_schemas
from app.schemas import billing as billing_schemas
from app.api import deps
from app.services.whatsapp import send_whatsapp_notification
from app.services.email import send_email_notification
from app.config import settings

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])

@router.get("/mapa", response_model=List[proveedor_schemas.ProveedorResponse])
def get_proveedores_mapa(
    categoria: Optional[models.CategoriaProveedor] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna la lista de proveedores activos para mostrar en el mapa interactivo.
    Permite filtrar por categoría y solo incluye proveedores con estado 'ACTIVO'.
    """
    query = db.query(models.ProveedorServicio).join(
        models.UsuarioSistema, models.ProveedorServicio.usuario_id == models.UsuarioSistema.id
    ).filter(
        models.UsuarioSistema.estado == models.EstadoUsuario.ACTIVO
    )
    
    if categoria:
        query = query.filter(models.ProveedorServicio.categoria == categoria)
        
    proveedores = query.all()
    
    result = []
    for prov in proveedores:
        user = prov.usuario
        result.append(
            proveedor_schemas.ProveedorResponse(
                id=prov.id,
                usuario_id=prov.usuario_id,
                ruc_cedula=prov.ruc_cedula,
                nombre_comercial=prov.nombre_comercial,
                celular_whatsapp=prov.celular_whatsapp,
                categoria=prov.categoria,
                especialidad=prov.especialidad,
                latitud=prov.latitud,
                longitud=prov.longitud,
                precio_consulta=prov.precio_consulta,
                imagen_url=prov.imagen_url,
                membresia_fija=prov.membresia_fija,
                es_premium=prov.es_premium,
                created_at=prov.created_at,
                email=user.email,
                estado=user.estado,
                link_tiktok=prov.link_tiktok if prov.es_premium else None,
                link_instagram=prov.link_instagram if prov.es_premium else None,
                link_facebook=prov.link_facebook if prov.es_premium else None,
                ciudad=prov.ciudad,
                sector=prov.sector,
                servicios_adicionales=prov.servicios_adicionales,
                google_calendar_link=prov.google_calendar_link if prov.es_premium else None
            )
        )
    return result

@router.post("/{id}/contactar", status_code=status.HTTP_201_CREATED)
async def contactar_proveedor(
    id: str,
    background_tasks: BackgroundTasks,
    current_user: models.UsuarioSistema = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Acción de contactar a un proveedor.
    1. Registra el evento de clic en la base de datos.
    2. Envía notificaciones asíncronas por WhatsApp y Correo.
    """
    if current_user.rol != models.RolUsuario.PACIENTE:
        raise HTTPException(
            status_code=403,
            detail="Solo los pacientes registrados pueden contactar proveedores"
        )
        
    paciente = db.query(models.Paciente).filter(
        models.Paciente.usuario_id == current_user.id
    ).first()
    
    if not paciente:
        raise HTTPException(
            status_code=404,
            detail="Perfil de paciente no encontrado"
        )
        
    proveedor = db.query(models.ProveedorServicio).join(
        models.UsuarioSistema, models.ProveedorServicio.usuario_id == models.UsuarioSistema.id
    ).filter(
        models.ProveedorServicio.id == id,
        models.UsuarioSistema.estado == models.EstadoUsuario.ACTIVO
    ).first()
    
    if not proveedor:
        raise HTTPException(
            status_code=404,
            detail="Proveedor no encontrado o no está activo"
        )
        
    # 1. Registrar clic de contacto (lead inicializado en CONTACTADO)
    nuevo_clic = models.EventoClicBilling(
        proveedor_id=proveedor.id,
        paciente_id=paciente.id,
        estado_lead=models.EstadoLeadCrm.CONTACTADO
    )
    db.add(nuevo_clic)
    db.commit()
    
    # 2. Programar notificaciones en segundo plano
    background_tasks.add_task(
        send_whatsapp_notification,
        provider_phone=proveedor.celular_whatsapp,
        patient_name=paciente.nombres,
        patient_lastname=paciente.apellidos,
        patient_cedula=paciente.cedula
    )
    
    email_body = (
        f"<h2>Nuevo Prospecto en Medic YA</h2>"
        f"<p>Estimado/a <strong>{proveedor.nombre_comercial}</strong>,</p>"
        f"<p>Un paciente ha solicitado tus datos de contacto:</p>"
        f"<ul>"
        f"  <li><strong>Nombre:</strong> {paciente.nombres} {paciente.apellidos}</li>"
        f"  <li><strong>Cédula:</strong> {paciente.cedula}</li>"
        f"  <li><strong>Celular/WhatsApp:</strong> {paciente.celular_whatsapp}</li>"
        f"  <li><strong>Correo:</strong> {current_user.email}</li>"
        f"</ul>"
        f"<p>¡Ponte en contacto lo antes posible!</p>"
    )
    
    background_tasks.add_task(
        send_email_notification,
        to_email=proveedor.usuario.email,
        subject="Medic YA - ¡Nuevo paciente interesado!",
        body=email_body
    )
    
    return {"message": "Contacto registrado exitosamente y notificaciones enviadas"}

@router.get("/dashboard/metricas", response_model=billing_schemas.MetricasProveedor)
def get_dashboard_metricas(
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Retorna las métricas en tiempo real para el panel del proveedor incluyendo
    el estado del lead crm, membresía ajustada ($15 si es Premium) y balance acumulado.
    """
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    
    if not proveedor:
        raise HTTPException(
            status_code=404,
            detail="Perfil de proveedor no encontrado"
        )
        
    # Obtener total de clics recibidos por este proveedor
    total_clics = db.query(models.EventoClicBilling).filter(
        models.EventoClicBilling.proveedor_id == proveedor.id
    ).count()
    
    # Calcular balance acumulado: membresía fija + ($5 por cada 1000 clics)
    clics_pagables = math.floor(total_clics / 1000)
    monto_adicional_clics = Decimal(clics_pagables) * Decimal("5.00")
    
    # Ajustar membresía: Premium $40, Básico $25
    membresia_fija = Decimal("40.00") if proveedor.es_premium else Decimal("25.00")
    balance_acumulado = membresia_fija + monto_adicional_clics
    
    # Obtener lista de prospectos detallada (leads con id y estado CRM)
    eventos = db.query(models.EventoClicBilling).filter(
        models.EventoClicBilling.proveedor_id == proveedor.id
    ).order_by(models.EventoClicBilling.created_at.desc()).all()
    
    prospectos_list = []
    for evt in eventos:
        if evt.paciente:
            prospectos_list.append(
                billing_schemas.ProspectoInfo(
                    id=evt.id,
                    nombres=evt.paciente.nombres,
                    apellidos=evt.paciente.apellidos,
                    cedula=evt.paciente.cedula,
                    celular_whatsapp=evt.paciente.celular_whatsapp if proveedor.es_premium else "Oculto (Solo Premium)",
                    email=evt.paciente.usuario.email if proveedor.es_premium else "Oculto (Solo Premium)",
                    estado_lead=evt.estado_lead,
                    fecha_contacto=evt.created_at,
                    link_tiktok=evt.paciente.link_tiktok if proveedor.es_premium else None,
                    link_instagram=evt.paciente.link_instagram if proveedor.es_premium else None,
                    link_facebook=evt.paciente.link_facebook if proveedor.es_premium else None
                )
            )
            
    return billing_schemas.MetricasProveedor(
        clics_recibidos=total_clics,
        prospectos_generados=len(prospectos_list),
        balance_acumulado=balance_acumulado,
        membresia_fija=membresia_fija,
        estado_cuenta=current_user.estado.value,
        lista_prospectos=prospectos_list,
        es_premium=proveedor.es_premium,
        link_tiktok=proveedor.link_tiktok,
        link_instagram=proveedor.link_instagram,
        link_facebook=proveedor.link_facebook
    )

# --- NUEVOS ENDPOINTS: CRM, CAMPAÑAS, REDENCIÓN QR Y RESEÑAS ---

@router.put("/leads/{clic_id}/estado")
def update_lead_status(
    clic_id: str,
    status_in: billing_schemas.LeadStatusUpdate,
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Permite al proveedor cambiar el estado CRM de un lead recibido (WhatsApp).
    """
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    
    lead = db.query(models.EventoClicBilling).filter(
        models.EventoClicBilling.id == clic_id,
        models.EventoClicBilling.proveedor_id == proveedor.id
    ).first()
    
    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead no encontrado"
        )
        
    lead.estado_lead = status_in.estado_lead
    db.commit()
    return {"message": f"Estado del lead actualizado a {status_in.estado_lead.value}"}

@router.post("/campanas", response_model=billing_schemas.CampanaResponse, status_code=status.HTTP_201_CREATED)
def create_campana(
    campana_in: billing_schemas.CampanaCreate,
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Crea una campaña de descuento propia. Exclusivo para proveedores PREMIUM ($15/mes).
    """
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    
    if not proveedor.es_premium:
        raise HTTPException(
            status_code=403,
            detail="Funcionalidad exclusiva para perfiles PREMIUM de $15.00/mes"
        )
        
    # Verificar que el código sea único
    existente = db.query(models.CampanaDescuento).filter(
        models.CampanaDescuento.codigo == campana_in.codigo
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe una campaña con este código promocional")
        
    nueva_campana = models.CampanaDescuento(
        proveedor_id=proveedor.id,
        codigo=campana_in.codigo.upper(),
        monto=campana_in.monto,
        limite_usos=campana_in.limite_usos,
        usos_actuales=0
    )
    db.add(nueva_campana)
    db.commit()
    db.refresh(nueva_campana)
    return nueva_campana

@router.get("/campanas", response_model=List[billing_schemas.CampanaResponse])
def get_mis_campanas(
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Retorna las campañas creadas por el proveedor autenticado.
    """
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    
    return db.query(models.CampanaDescuento).filter(
        models.CampanaDescuento.proveedor_id == proveedor.id
    ).all()

@router.get("/{id}/campanas", response_model=List[billing_schemas.CampanaResponse])
def get_campanas_publicas(
    id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna las campañas activas de un proveedor para que el paciente las pueda ver.
    """
    return db.query(models.CampanaDescuento).filter(
        models.CampanaDescuento.proveedor_id == id
    ).all()

@router.post("/canjear-campana", status_code=status.HTTP_201_CREATED)
def canjear_campana_codigo(
    codigo_campana: str,
    current_user: models.UsuarioSistema = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
):
    """
    El paciente canjea el código de campaña de un médico Premium,
    creando un cupón restringido a ese médico en su billetera.
    """
    if current_user.rol != models.RolUsuario.PACIENTE:
        raise HTTPException(status_code=403, detail="Solo los pacientes pueden canjear campañas")
        
    paciente = db.query(models.Paciente).filter(models.Paciente.usuario_id == current_user.id).first()
    campana = db.query(models.CampanaDescuento).filter(models.CampanaDescuento.codigo == codigo_campana.upper()).first()
    
    if not campana:
        raise HTTPException(status_code=404, detail="Código de campaña no encontrado")
        
    if campana.usos_actuales >= campana.limite_usos:
        raise HTTPException(status_code=400, detail="Esta campaña ha alcanzado su límite máximo de usos")
        
    # Verificar si el paciente ya tiene este cupón de campaña activo
    cupon_existente = db.query(models.Cupon).filter(
        models.Cupon.paciente_id == paciente.id,
        models.Cupon.campana_id == campana.id,
        models.Cupon.estado == models.EstadoCupon.ACTIVO
    ).first()
    if cupon_existente:
        raise HTTPException(status_code=400, detail="Ya tienes este cupón activo en tu billetera")
        
    # Generar el cupón de campaña
    codigo_cupon = f"CAMP-{campana.codigo}-{str(uuid.uuid4())[:6].upper()}"
    nuevo_cupon = models.Cupon(
        paciente_id=paciente.id,
        codigo=codigo_cupon,
        monto=campana.monto,
        campana_id=campana.id,
        estado=models.EstadoCupon.ACTIVO
    )
    db.add(nuevo_cupon)
    
    # Incrementar el uso de la campaña
    campana.usos_actuales += 1
    db.add(campana)
    db.commit()
    
    return {"message": "¡Cupón agregado exitosamente a tu billetera!", "cupon": codigo_cupon}

@router.post("/redimir-cupon")
def redimir_cupon(
    codigo: str,
    background_tasks: BackgroundTasks,
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    """
    El proveedor escanea/ingresa el código del cupón dinámico del paciente para "quemarlo" (redimirlo).
    Aplica la lógica de "Invita y Gana" al momento de la primera consulta del referido.
    """
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    
    cupon = db.query(models.Cupon).filter(
        models.Cupon.codigo == codigo.upper(),
        models.Cupon.estado == models.EstadoCupon.ACTIVO
    ).first()
    
    if not cupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado o ya ha sido redimido")
        
    # Si proviene de una campaña, validar que sea con este proveedor
    if cupon.campana_id:
        campana = db.query(models.CampanaDescuento).filter(models.CampanaDescuento.id == cupon.campana_id).first()
        if campana and campana.proveedor_id != proveedor.id:
            raise HTTPException(status_code=400, detail="Este cupón es de campaña de otro profesional y no puede ser usado aquí")
            
    # Marcar el cupón como REDIMIDO
    cupon.estado = models.EstadoCupon.REDIMIDO
    cupon.proveedor_redencion_id = proveedor.id
    cupon.fecha_redencion = datetime.utcnow()
    db.add(cupon)
    
    # Actualizar backward compatibility column si es cupón de bienvenida
    paciente = cupon.paciente
    if codigo.upper().startswith("WELCOME-"):
        paciente.cupon_usado = True
        db.add(paciente)
        
    # --- PROGRAMA DE REFERIDOS: "INVITA Y GANA" ---
    # Si es el primer cupón que redime el paciente y fue referido por alguien
    if paciente.referido_por_id:
        consultas_previas = db.query(models.Cupon).filter(
            models.Cupon.paciente_id == paciente.id,
            models.Cupon.estado == models.EstadoCupon.REDIMIDO,
            models.Cupon.id != cupon.id
        ).count()
        
        if consultas_previas == 0:
            # Otorga $5 USD al referidor (patrocinador)
            codigo_patrocinador = f"REF-{str(uuid.uuid4())[:8].upper()}"
            cupon_patrocinador = models.Cupon(
                paciente_id=paciente.referido_por_id,
                codigo=codigo_patrocinador,
                monto=5.00,
                estado=models.EstadoCupon.ACTIVO
            )
            db.add(cupon_patrocinador)
            
            # Otorga otro cupón de $5 USD al nuevo paciente (incentivo extra)
            codigo_nuevo = f"REWARD-{str(uuid.uuid4())[:8].upper()}"
            cupon_nuevo = models.Cupon(
                paciente_id=paciente.id,
                codigo=codigo_nuevo,
                monto=5.00,
                estado=models.EstadoCupon.ACTIVO
            )
            db.add(cupon_nuevo)
            
            # WhatsApp al patrocinador avisando de su recompensa
            patrocinador = db.query(models.Paciente).filter(models.Paciente.id == paciente.referido_por_id).first()
            if patrocinador:
                background_tasks.add_task(
                    send_whatsapp_notification,
                    provider_phone=patrocinador.celular_whatsapp,
                    patient_name=patrocinador.nombres,
                    patient_lastname="Gana",
                    patient_cedula="¡Referido Exitoso! Tienes un nuevo cupón de $5.00 USD acumulable en Medic YA."
                )
                
    db.commit()
    return {"message": "¡Cupón redimido con éxito!", "monto_descuento": float(cupon.monto)}

@router.post("/{id}/resenas", status_code=status.HTTP_201_CREATED)
def dejar_resena(
    id: str,
    resena_in: billing_schemas.ResenaCreate,
    current_user: models.UsuarioSistema = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dejar una calificación verificada.
    El paciente debe haber redimido un cupón previamente con este proveedor.
    """
    if current_user.rol != models.RolUsuario.PACIENTE:
        raise HTTPException(status_code=403, detail="Solo los pacientes pueden escribir reseñas")
        
    paciente = db.query(models.Paciente).filter(models.Paciente.usuario_id == current_user.id).first()
    
    # Comprobar redención verificada
    fue_atendido = db.query(models.Cupon).filter(
        models.Cupon.paciente_id == paciente.id,
        models.Cupon.proveedor_redencion_id == id,
        models.Cupon.estado == models.EstadoCupon.REDIMIDO
    ).first()
    
    if not fue_atendido:
        raise HTTPException(
            status_code=403,
            detail="Solo puedes escribir una reseña si has asistido a consulta y redimido un cupón con este profesional"
        )
        
    # Verificar si ya dejó reseña previa
    existente = db.query(models.Resena).filter(
        models.Resena.proveedor_id == id,
        models.Resena.paciente_id == paciente.id
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya has calificado a este proveedor anteriormente")
        
    nueva_resena = models.Resena(
        proveedor_id=id,
        paciente_id=paciente.id,
        calificacion=resena_in.calificacion,
        comentario=resena_in.comentario
    )
    db.add(nueva_resena)
    db.commit()
    return {"message": "Reseña registrada con éxito"}

@router.get("/{id}/resenas", response_model=List[billing_schemas.ResenaResponse])
def get_resenas_proveedor(
    id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna la lista de reseñas de un proveedor específico.
    """
    resenas = db.query(models.Resena).filter(models.Resena.proveedor_id == id).order_by(models.Resena.created_at.desc()).all()
    result = []
    for r in resenas:
        result.append(
            billing_schemas.ResenaResponse(
                id=r.id,
                proveedor_id=r.proveedor_id,
                paciente_id=r.paciente_id,
                paciente_nombre=f"{r.paciente.nombres} {r.paciente.apellidos[0]}.", # Ofuscar apellido
                calificacion=r.calificacion,
                comentario=r.comentario,
                created_at=r.created_at
            )
        )
    return result

@router.post("/upgrade-simulado")
def upgrade_provider_to_premium(
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    proveedor.es_premium = True
    proveedor.membresia_fija = Decimal("15.00")
    db.commit()
    return {"message": "Suscripción Premium activada exitosamente", "membresia_fija": 15.00}

@router.post("/solicitar-publicidad", status_code=status.HTTP_201_CREATED)
def solicitar_publicidad_proveedor(
    pub_in: billing_schemas.SolicitudPublicidadCreate,
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Permite al doctor contratar publicidad en redes sociales.
    Suma el precio al monto de publicidad de su factura pendiente actual o crea una nueva factura.
    """
    from datetime import date, timedelta
    
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    # 1. Crear registro de SolicitudPublicidad
    nueva_solicitud = models.SolicitudPublicidad(
        usuario_id=current_user.id,
        plataformas=pub_in.plataformas,
        cantidad_vistas=pub_in.cantidad_vistas,
        precio=pub_in.precio,
        estado="PENDIENTE",
        veces_publicado=0
    )
    db.add(nueva_solicitud)
    db.flush()
    
    # 2. Buscar factura pendiente del mes corriente para sumarle el cobro
    factura = db.query(models.Factura).filter(
        models.Factura.proveedor_id == proveedor.id,
        models.Factura.estado == models.EstadoFactura.PENDIENTE
    ).first()
    
    monto_pub = Decimal(str(pub_in.precio))
    if factura:
        factura.monto_publicidad = (factura.monto_publicidad or Decimal("0.00")) + monto_pub
        factura.monto_total += monto_pub
        db.add(factura)
    else:
        # Si no tiene factura pendiente, crear una nueva con el costo de la publicidad
        fecha_vencimiento = date.today() + timedelta(days=10)
        factura = models.Factura(
            proveedor_id=proveedor.id,
            fecha_emision=date.today(),
            fecha_vencimiento=fecha_vencimiento,
            monto_fijo=Decimal("0.00"),
            monto_clics=Decimal("0.00"),
            monto_publicidad=monto_pub,
            monto_total=monto_pub,
            estado=models.EstadoFactura.PENDIENTE
        )
        db.add(factura)
        
    db.commit()
    return {"message": "Solicitud de publicidad contratada con éxito y cargada a su factura", "solicitud_id": nueva_solicitud.id}

@router.put("/me/redes")
def update_provider_redes(
    redes_in: proveedor_schemas.ProveedorRedesUpdate,
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Actualiza los enlaces de redes sociales del proveedor.
    Solo permitido si el proveedor tiene suscripción Premium activa.
    """
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    if not proveedor.es_premium:
        raise HTTPException(
            status_code=403,
            detail="Para agregar redes sociales a tu perfil debes contar con la suscripción Premium."
        )
        
    proveedor.link_tiktok = redes_in.link_tiktok
    proveedor.link_instagram = redes_in.link_instagram
    proveedor.link_facebook = redes_in.link_facebook
    
    db.commit()
    return {"message": "Redes sociales actualizadas exitosamente."}


# --- ENDPOINTS DE AGENDA Y CALENDARIO PARA PROVEEDORES PREMIUM ---

@router.get("/me/agenda-config", response_model=proveedor_schemas.ConfiguracionAgendaResponse)
def get_agenda_config(
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Retorna la configuración de la agenda para el proveedor actual.
    Si no existe y es Premium, se auto-crea con valores por defecto.
    """
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    if not proveedor.es_premium:
        raise HTTPException(
            status_code=403,
            detail="La funcionalidad de Agenda y Calendario está reservada únicamente para cuentas Premium."
        )
        
    config = db.query(models.ConfiguracionAgendaProveedor).filter(
        models.ConfiguracionAgendaProveedor.proveedor_id == proveedor.id
    ).first()
    
    if not config:
        horarios_default = {
            "lunes": ["09:00", "17:00"],
            "martes": ["09:00", "17:00"],
            "miercoles": ["09:00", "17:00"],
            "jueves": ["09:00", "17:00"],
            "viernes": ["09:00", "17:00"]
        }
        config = models.ConfiguracionAgendaProveedor(
            proveedor_id=proveedor.id,
            horarios_disponibilidad=horarios_default,
            duracion_turno=30,
            respuesta_automatica="Hola, gracias por contactarme. He recibido tu solicitud. Estaré encantado de atenderte."
        )
        db.add(config)
        db.commit()
        db.refresh(config)
        
    return proveedor_schemas.ConfiguracionAgendaResponse(
        id=config.id,
        proveedor_id=config.proveedor_id,
        horarios_disponibilidad=config.horarios_disponibilidad,
        duracion_turno=config.duracion_turno,
        respuesta_automatica=config.respuesta_automatica,
        created_at=config.created_at,
        google_calendar_link=proveedor.google_calendar_link
    )


@router.put("/me/agenda-config", response_model=proveedor_schemas.ConfiguracionAgendaResponse)
def update_agenda_config(
    config_in: proveedor_schemas.ConfiguracionAgendaUpdate,
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Actualiza la configuración de disponibilidad y mensaje automático de la agenda del proveedor.
    """
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    if not proveedor.es_premium:
        raise HTTPException(
            status_code=403,
            detail="La funcionalidad de Agenda y Calendario está reservada únicamente para cuentas Premium."
        )
        
    config = db.query(models.ConfiguracionAgendaProveedor).filter(
        models.ConfiguracionAgendaProveedor.proveedor_id == proveedor.id
    ).first()
    
    if not config:
        config = models.ConfiguracionAgendaProveedor(proveedor_id=proveedor.id)
        db.add(config)
        
    if config_in.horarios_disponibilidad is not None:
        config.horarios_disponibilidad = config_in.horarios_disponibilidad
    if config_in.duracion_turno is not None:
        config.duracion_turno = config_in.duracion_turno
    if config_in.respuesta_automatica is not None:
        config.respuesta_automatica = config_in.respuesta_automatica
    if config_in.google_calendar_link is not None:
        proveedor.google_calendar_link = config_in.google_calendar_link
        
    db.commit()
    db.refresh(config)
    db.refresh(proveedor)
    
    return proveedor_schemas.ConfiguracionAgendaResponse(
        id=config.id,
        proveedor_id=config.proveedor_id,
        horarios_disponibilidad=config.horarios_disponibilidad,
        duracion_turno=config.duracion_turno,
        respuesta_automatica=config.respuesta_automatica,
        created_at=config.created_at,
        google_calendar_link=proveedor.google_calendar_link
    )


@router.get("/me/citas", response_model=List[proveedor_schemas.CitaResponse])
def get_provider_citas(
    fecha: Optional[str] = None,
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Retorna la lista de citas reservadas y bloques de agenda del proveedor actual.
    """
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    query = db.query(models.CitaProveedor).filter(
        models.CitaProveedor.proveedor_id == proveedor.id
    )
    if fecha:
        query = query.filter(models.CitaProveedor.fecha == fecha)
        
    return query.order_by(models.CitaProveedor.fecha.asc(), models.CitaProveedor.hora_inicio.asc()).all()


@router.post("/me/citas", response_model=proveedor_schemas.CitaResponse)
def create_provider_cita_manual(
    cita_in: proveedor_schemas.CitaCreate,
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Permite al proveedor bloquear turnos manualmente o registrar citas de forma directa.
    """
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    # Verificar solapamiento
    solapada = db.query(models.CitaProveedor).filter(
        models.CitaProveedor.proveedor_id == proveedor.id,
        models.CitaProveedor.fecha == cita_in.fecha,
        models.CitaProveedor.hora_inicio < cita_in.hora_fin,
        models.CitaProveedor.hora_fin > cita_in.hora_inicio
    ).first()
    if solapada:
        raise HTTPException(status_code=400, detail="El horario seleccionado se solapa con una cita o bloqueo existente.")
        
    nueva_cita = models.CitaProveedor(
        proveedor_id=proveedor.id,
        paciente_nombre=cita_in.paciente_nombre,
        fecha=cita_in.fecha,
        hora_inicio=cita_in.hora_inicio,
        hora_fin=cita_in.hora_fin,
        estado=cita_in.estado
    )
    db.add(nueva_cita)
    db.commit()
    db.refresh(nueva_cita)
    return nueva_cita


@router.delete("/me/citas/{cita_id}")
def delete_provider_cita(
    cita_id: str,
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Elimina o cancela una cita/bloqueo de la agenda del proveedor.
    """
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    cita = db.query(models.CitaProveedor).filter(
        models.CitaProveedor.id == cita_id,
        models.CitaProveedor.proveedor_id == proveedor.id
    ).first()
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
        
    db.delete(cita)
    db.commit()
    return {"message": "Cita o bloqueo eliminado exitosamente."}


@router.get("/{id}/agenda-disponibilidad")
def get_public_agenda_disponibilidad(
    id: str,
    fecha: str, # Formato YYYY-MM-DD
    db: Session = Depends(get_db)
):
    """
    Retorna la disponibilidad pública de turnos para un doctor específico en una fecha dada.
    """
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.id == id
    ).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    if not proveedor.es_premium:
        return {"es_premium": False, "slots": []}
        
    config = db.query(models.ConfiguracionAgendaProveedor).filter(
        models.ConfiguracionAgendaProveedor.proveedor_id == proveedor.id
    ).first()
    
    try:
        import datetime as dt_mod
        dt_val = dt_mod.datetime.strptime(fecha, "%Y-%m-%d")
        dias_map = {
            0: "lunes", 1: "martes", 2: "miercoles",
            3: "jueves", 4: "viernes", 5: "sabado", 6: "domingo"
        }
        dia_semana = dias_map[dt_val.weekday()]
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Utilice YYYY-MM-DD")
        
    horarios_disponibilidad = {}
    duracion = 30
    resp_automatica = "Hola, gracias por cotizar conmigo. Estaré atento a tu consulta."
    if config:
        horarios_disponibilidad = config.horarios_disponibilidad or {}
        duracion = config.duracion_turno or 30
        resp_automatica = config.respuesta_automatica or resp_automatica
    else:
        horarios_default = {
            "lunes": ["09:00", "17:00"], "martes": ["09:00", "17:00"], "miercoles": ["09:00", "17:00"],
            "jueves": ["09:00", "17:00"], "viernes": ["09:00", "17:00"]
        }
        horarios_disponibilidad = horarios_default
        
    slots_dia = horarios_disponibilidad.get(dia_semana)
    if not slots_dia or len(slots_dia) < 2:
        return {"es_premium": True, "respuesta_automatica": resp_automatica, "slots": []}
        
    start_str, end_str = slots_dia[0], slots_dia[1]
    
    try:
        start_time = dt_mod.datetime.strptime(start_str, "%H:%M")
        end_time = dt_mod.datetime.strptime(end_str, "%H:%M")
    except Exception:
        return {"es_premium": True, "respuesta_automatica": resp_automatica, "slots": []}
        
    slots = []
    current_time = start_time
    while current_time + dt_mod.timedelta(minutes=duracion) <= end_time:
        slot_start = current_time.strftime("%H:%M")
        next_time = current_time + dt_mod.timedelta(minutes=duracion)
        slot_end = next_time.strftime("%H:%M")
        slots.append({
            "hora_inicio": slot_start,
            "hora_fin": slot_end,
            "libre": True
        })
        current_time = next_time
        
    citas_existentes = db.query(models.CitaProveedor).filter(
        models.CitaProveedor.proveedor_id == proveedor.id,
        models.CitaProveedor.fecha == fecha
    ).all()
    
    for slot in slots:
        for cita in citas_existentes:
            if slot["hora_inicio"] < cita.hora_fin and slot["hora_fin"] > cita.hora_inicio:
                slot["libre"] = False
                break
                
    # Deshabilitar turnos pasados si la fecha consultada es hoy en Ecuador (UTC-5)
    from datetime import datetime, timezone, timedelta
    now_ecuador = datetime.now(timezone.utc) - timedelta(hours=5)
    today_ecuador_str = now_ecuador.strftime("%Y-%m-%d")
    if fecha == today_ecuador_str:
        now_time_str = now_ecuador.strftime("%H:%M")
        for slot in slots:
            if slot["hora_inicio"] < now_time_str:
                slot["libre"] = False
                
    return {
        "es_premium": True,
        "respuesta_automatica": resp_automatica,
        "slots": slots
    }


@router.post("/{id}/reservar-cita", response_model=proveedor_schemas.CitaResponse)
def reservar_cita_public(
    id: str,
    cita_in: proveedor_schemas.CitaCreate,
    background_tasks: BackgroundTasks,
    current_user: models.UsuarioSistema = Depends(deps.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permite a un paciente registrado reservar una cita en la disponibilidad del proveedor.
    """
    if current_user.rol != models.RolUsuario.PACIENTE:
        raise HTTPException(status_code=403, detail="Solo los pacientes registrados pueden reservar citas.")
        
    paciente = db.query(models.Paciente).filter(models.Paciente.usuario_id == current_user.id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
        
    proveedor = db.query(models.ProveedorServicio).filter(models.ProveedorServicio.id == id).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    if not proveedor.es_premium:
        raise HTTPException(status_code=400, detail="Este proveedor no acepta reservaciones automáticas.")
        
    # Evitar reservar turnos en el pasado (Ecuador UTC-5)
    from datetime import datetime, timezone, timedelta
    now_ecuador = datetime.now(timezone.utc) - timedelta(hours=5)
    today_ecuador_str = now_ecuador.strftime("%Y-%m-%d")
    if cita_in.fecha < today_ecuador_str or (cita_in.fecha == today_ecuador_str and cita_in.hora_inicio < now_ecuador.strftime("%H:%M")):
        raise HTTPException(status_code=400, detail="No puedes reservar un turno en el pasado.")
        
    # Verificar solapamiento
    solapada = db.query(models.CitaProveedor).filter(
        models.CitaProveedor.proveedor_id == proveedor.id,
        models.CitaProveedor.fecha == cita_in.fecha,
        models.CitaProveedor.hora_inicio < cita_in.hora_fin,
        models.CitaProveedor.hora_fin > cita_in.hora_inicio
    ).first()
    if solapada:
        raise HTTPException(
            status_code=400,
            detail=f"El horario {cita_in.hora_inicio} a {cita_in.hora_fin} para el día {cita_in.fecha} ya no está disponible."
        )
        
    nueva_cita = models.CitaProveedor(
        proveedor_id=proveedor.id,
        paciente_id=paciente.id,
        paciente_nombre=cita_in.paciente_nombre,
        fecha=cita_in.fecha,
        hora_inicio=cita_in.hora_inicio,
        hora_fin=cita_in.hora_fin,
        estado="RESERVADA",
        servicios=cita_in.servicios
    )
    db.add(nueva_cita)
    db.commit()
    db.refresh(nueva_cita)
    
    # Sincronización simulada con Google Calendar si el doctor configuró su cuenta/link
    if proveedor.google_calendar_link:
        print(f"📅 [Google Calendar Sync] Creando evento en Google Calendar del Dr. {proveedor.nombre_comercial}")
        print(f"   Evento: Cita con {nueva_cita.paciente_nombre} ({nueva_cita.fecha} de {nueva_cita.hora_inicio} a {nueva_cita.hora_fin})")

    # Enviar respuesta automática del profesional al celular de WhatsApp del paciente
    config = db.query(models.ConfiguracionAgendaProveedor).filter(
        models.ConfiguracionAgendaProveedor.proveedor_id == proveedor.id
    ).first()
    if config and config.respuesta_automatica and paciente.celular_whatsapp:
        from app.services.whatsapp import send_custom_whatsapp
        background_tasks.add_task(
            send_custom_whatsapp,
            to_phone=paciente.celular_whatsapp,
            message=config.respuesta_automatica
        )

    return nueva_cita


@router.put("/me/citas/{cita_id}", response_model=proveedor_schemas.CitaResponse)
def update_cita(
    cita_id: str,
    cita_in: proveedor_schemas.CitaUpdate,
    current_user: models.UsuarioSistema = Depends(deps.get_current_provider),
    db: Session = Depends(get_db)
):
    """
    Permite al doctor reprogramar una cita o bloqueo de su agenda.
    """
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.usuario_id == current_user.id
    ).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    cita = db.query(models.CitaProveedor).filter(
        models.CitaProveedor.id == cita_id,
        models.CitaProveedor.proveedor_id == proveedor.id
    ).first()
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
        
    # Verificar solapamiento si se cambia el horario
    if (cita_in.hora_inicio != cita.hora_inicio or 
        cita_in.hora_fin != cita.hora_fin or 
        cita_in.fecha != cita.fecha):
        solapada = db.query(models.CitaProveedor).filter(
            models.CitaProveedor.proveedor_id == proveedor.id,
            models.CitaProveedor.fecha == cita_in.fecha,
            models.CitaProveedor.id != cita.id,
            models.CitaProveedor.hora_inicio < cita_in.hora_fin,
            models.CitaProveedor.hora_fin > cita_in.hora_inicio
        ).first()
        if solapada:
            raise HTTPException(status_code=400, detail="El horario seleccionado ya no está disponible o se solapa.")
            
    cita.fecha = cita_in.fecha
    cita.hora_inicio = cita_in.hora_inicio
    cita.hora_fin = cita_in.hora_fin
    if cita_in.estado is not None:
        cita.estado = cita_in.estado
    if cita_in.servicios is not None:
        cita.servicios = cita_in.servicios
        
    db.commit()
    db.refresh(cita)

    # Notificar en consola sincronización con Google Calendar
    if proveedor.google_calendar_link:
        print(f"📅 [Google Calendar Sync] Actualizando/Reprogramando evento en Google Calendar del Dr. {proveedor.nombre_comercial}")
        print(f"   Evento Actualizado: Cita con {cita.paciente_nombre} ({cita.fecha} de {cita.hora_inicio} a {cita.hora_fin})")

    return cita


@router.post("/cron/send-today-report")
async def trigger_today_report(
    token: str = Query(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Endpoint seguro para disparar el reporte de atenciones de hoy de forma externa.
    """
    if token != settings.CRON_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Token de seguridad inválido")
        
    from app.services.report_cron import send_all_doctors_today_reports
    if background_tasks:
        background_tasks.add_task(send_all_doctors_today_reports, db)
        return {"status": "processing", "message": "Enviando reportes de hoy en segundo plano"}
    else:
        await send_all_doctors_today_reports(db)
        return {"status": "success", "message": "Reportes de hoy enviados con éxito"}


@router.post("/cron/send-tomorrow-report")
async def trigger_tomorrow_report(
    token: str = Query(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Endpoint seguro para disparar el reporte de agenda de mañana de forma externa.
    """
    if token != settings.CRON_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Token de seguridad inválido")
        
    from app.services.report_cron import send_all_doctors_tomorrow_reports
    if background_tasks:
        background_tasks.add_task(send_all_doctors_tomorrow_reports, db)
        return {"status": "processing", "message": "Enviando reportes de mañana en segundo plano"}
    else:
        await send_all_doctors_tomorrow_reports(db)
        return {"status": "success", "message": "Reportes de mañana enviados con éxito"}


