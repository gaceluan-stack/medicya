from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from decimal import Decimal
from app.db.database import get_db
from app.db import models
from app.schemas import proveedor as proveedor_schemas
from app.schemas import billing as billing_schemas
from app.api import deps

router = APIRouter(prefix="/admin", tags=["Administración"])

@router.post("/proveedores", response_model=proveedor_schemas.ProveedorResponse, status_code=status.HTTP_201_CREATED)
def create_proveedor(
    prov_in: proveedor_schemas.ProveedorCreate,
    current_admin: models.UsuarioSistema = Depends(deps.get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo proveedor en el sistema.
    Solamente accesible por el Administrador. Crea la credencial de acceso y su perfil.
    """
    # 1. Verificar si ya existe un usuario con el mismo email
    usuario_existente = db.query(models.UsuarioSistema).filter(
        models.UsuarioSistema.email == prov_in.email
    ).first()
    if usuario_existente:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un usuario registrado con este correo electrónico"
        )
        
    # 2. Verificar si ya existe un proveedor con el mismo RUC/Cédula
    proveedor_existente = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.ruc_cedula == prov_in.ruc_cedula
    ).first()
    if proveedor_existente:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un proveedor registrado con este RUC/Cédula"
        )
        
    # 3. Crear el usuario del sistema base
    password_hash = deps.get_password_hash(prov_in.password)
    nuevo_usuario = models.UsuarioSistema(
        email=prov_in.email,
        password_hash=password_hash,
        rol=models.RolUsuario.PROVEEDOR,
        estado=models.EstadoUsuario.ACTIVO
    )
    db.add(nuevo_usuario)
    db.flush()
    
    # 4. Crear el perfil del proveedor
    from app.services.sector_classifier import classify_location
    _, sector_auto = classify_location(prov_in.latitud, prov_in.longitud)

    nuevo_proveedor = models.ProveedorServicio(
        usuario_id=nuevo_usuario.id,
        ruc_cedula=prov_in.ruc_cedula,
        nombre_comercial=prov_in.nombre_comercial,
        celular_whatsapp=prov_in.celular_whatsapp,
        categoria=prov_in.categoria,
        especialidad=prov_in.especialidad,
        latitud=prov_in.latitud,
        longitud=prov_in.longitud,
        precio_consulta=prov_in.precio_consulta,
        imagen_url=prov_in.imagen_url,
        membresia_fija=Decimal("40.00") if prov_in.es_premium else Decimal("25.00"),
        es_premium=prov_in.es_premium,
        link_tiktok=prov_in.link_tiktok,
        link_instagram=prov_in.link_instagram,
        link_facebook=prov_in.link_facebook,
        ciudad=prov_in.ciudad,
        sector=sector_auto
    )
    db.add(nuevo_proveedor)
    db.commit()
    db.refresh(nuevo_proveedor)
    
    return proveedor_schemas.ProveedorResponse(
        id=nuevo_proveedor.id,
        usuario_id=nuevo_proveedor.usuario_id,
        ruc_cedula=nuevo_proveedor.ruc_cedula,
        nombre_comercial=nuevo_proveedor.nombre_comercial,
        celular_whatsapp=nuevo_proveedor.celular_whatsapp,
        categoria=nuevo_proveedor.categoria,
        especialidad=nuevo_proveedor.especialidad,
        latitud=nuevo_proveedor.latitud,
        longitud=nuevo_proveedor.longitud,
        precio_consulta=nuevo_proveedor.precio_consulta,
        imagen_url=nuevo_proveedor.imagen_url,
        membresia_fija=nuevo_proveedor.membresia_fija,
        es_premium=nuevo_proveedor.es_premium,
        created_at=nuevo_proveedor.created_at,
        email=nuevo_usuario.email,
        estado=nuevo_usuario.estado,
        link_tiktok=nuevo_proveedor.link_tiktok,
        link_instagram=nuevo_proveedor.link_instagram,
        link_facebook=nuevo_proveedor.link_facebook,
        ciudad=nuevo_proveedor.ciudad,
        sector=nuevo_proveedor.sector
    )

@router.get("/atribucion", response_model=List[billing_schemas.ReporteAtribucion])
def get_reporte_atribucion(
    current_admin: models.UsuarioSistema = Depends(deps.get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Retorna un reporte de atribución publicitaria indicando cuántos pacientes
    provienen de cada canal (TikTok, Instagram, Facebook, Referido Personal).
    """
    total_pacientes = db.query(models.Paciente).count()
    if total_pacientes == 0:
        return [
            billing_schemas.ReporteAtribucion(origen=canal.value, cantidad=0, porcentaje=0.0)
            for canal in models.CanalAtribucion
        ]
        
    resultados = db.query(
        models.Paciente.origen_informacion,
        func.count(models.Paciente.id).label("cantidad")
    ).group_by(models.Paciente.origen_informacion).all()
    
    reporte = []
    canales_vistos = set()
    for res in resultados:
        canal = res[0]
        cant = res[1]
        canales_vistos.add(canal)
        porcentaje = round((cant / total_pacientes) * 100, 2)
        reporte.append(
            billing_schemas.ReporteAtribucion(
                origen=canal.value,
                cantidad=cant,
                porcentaje=porcentaje
            )
        )
        
    # Añadir los canales que tienen 0 registros
    for canal in models.CanalAtribucion:
        if canal not in canales_vistos:
            reporte.append(
                billing_schemas.ReporteAtribucion(
                    origen=canal.value,
                    cantidad=0,
                    porcentaje=0.0
                )
            )
            
    return reporte

@router.get("/proveedores", response_model=List[proveedor_schemas.ProveedorResponse])
def list_proveedores_admin(
    current_admin: models.UsuarioSistema = Depends(deps.get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Lista todos los proveedores registrados (sin importar si están activos o bloqueados).
    """
    proveedores = db.query(models.ProveedorServicio).all()
    result = []
    for prov in proveedores:
        user = prov.usuario
        result.append(
            proveedor_schemas.ProveedorResponse(
                id=prov.id,
                usuario_id=prov.usuario_id,
                ruc_cedula=prov.ruc_cedula,
                nombre_comercial=prov.nombre_comercial,
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
                link_tiktok=prov.link_tiktok,
                link_instagram=prov.link_instagram,
                link_facebook=prov.link_facebook,
                ciudad=prov.ciudad,
                sector=prov.sector
            )
        )
    return result

@router.post("/proveedores/{id}/estado")
def change_proveedor_estado(
    id: str,
    nuevo_estado: models.EstadoUsuario,
    current_admin: models.UsuarioSistema = Depends(deps.get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Permite al administrador cambiar el estado de cuenta de un proveedor
    (ej. activar un proveedor bloqueado tras cancelar su pago).
    """
    prov = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.id == id
    ).first()
    
    if not prov:
        raise HTTPException(
            status_code=404,
            detail="Proveedor no encontrado"
        )
        
    user = db.query(models.UsuarioSistema).filter(
        models.UsuarioSistema.id == prov.usuario_id
    ).first()
    
    user.estado = nuevo_estado
    db.commit()
    
    return {"message": f"Estado del proveedor cambiado exitosamente a {nuevo_estado.value}"}

@router.get("/usuarios")
def list_usuarios_admin(
    current_admin: models.UsuarioSistema = Depends(deps.get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Retorna el listado completo de usuarios en el sistema (Admin, Doctores y Pacientes).
    """
    usuarios = db.query(models.UsuarioSistema).all()
    result = []
    for u in usuarios:
        info = {
            "id": u.id,
            "email": u.email,
            "rol": u.rol.value if u.rol else None,
            "estado": u.estado.value if u.estado else None,
            "created_at": u.created_at,
            "detalle": ""
        }
        if u.rol == models.RolUsuario.PACIENTE and u.paciente:
            info["detalle"] = f"{u.paciente.nombres} {u.paciente.apellidos} (Cédula: {u.paciente.cedula})"
        elif u.rol == models.RolUsuario.PROVEEDOR and u.proveedor:
            info["detalle"] = f"{u.proveedor.nombre_comercial} ({u.proveedor.especialidad or 'Gral'})"
        elif u.rol == models.RolUsuario.ADMIN:
            info["detalle"] = "Administrador Global"
        result.append(info)
    return result

@router.post("/usuarios/{id}/estado")
def change_usuario_estado(
    id: str,
    nuevo_estado: models.EstadoUsuario,
    current_admin: models.UsuarioSistema = Depends(deps.get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Permite cambiar el estado de cualquier usuario del sistema.
    """
    user = db.query(models.UsuarioSistema).filter(
        models.UsuarioSistema.id == id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )
        
    user.estado = nuevo_estado
    db.commit()
    return {"message": f"Estado del usuario cambiado a {nuevo_estado.value} exitosamente."}

@router.get("/publicidad/campanas")
def list_publicidad_campanas(
    current_admin: models.UsuarioSistema = Depends(deps.get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Lista todas las solicitudes de publicidad registradas.
    """
    campanas = db.query(models.SolicitudPublicidad).all()
    result = []
    for c in campanas:
        result.append({
            "id": c.id,
            "usuario_id": c.usuario_id,
            "email": c.usuario.email if c.usuario else "N/A",
            "rol": c.usuario.rol.value if c.usuario else "N/A",
            "plataformas": c.plataformas,
            "cantidad_vistas": c.cantidad_vistas,
            "precio": float(c.precio),
            "estado": c.estado,
            "veces_publicado": c.veces_publicado,
            "created_at": c.created_at
        })
    return result

@router.post("/publicidad/ejecutar-agente")
def run_ad_agent_simulated(
    current_admin: models.UsuarioSistema = Depends(deps.get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Ejecuta el Agente IA de Publicación Diaria. Avanza el progreso de las campañas activas.
    """
    import random
    campanas_activas = db.query(models.SolicitudPublicidad).filter(
        models.SolicitudPublicidad.estado != "COMPLETADA"
    ).all()
    
    logs = []
    logs.append(f"🤖 [Agente IA] Iniciando procesamiento diario de publicidad en redes sociales...")
    
    if not campanas_activas:
        logs.append("🤖 [Agente IA] No hay campañas de publicidad activas para procesar hoy.")
        return {"logs": logs}
        
    for c in campanas_activas:
        client_email = c.usuario.email if c.usuario else "Usuario"
        plataformas_list = c.plataformas.split(",")
        
        # Cambiar estado a EN_CURSO si estaba PENDIENTE
        if c.estado == "PENDIENTE":
            c.estado = "EN_CURSO"
            logs.append(f"🚀 [Agente IA] Activando campaña ID {c.id[:8]} para {client_email} en plataformas: {c.plataformas}")
        
        # Generar progreso de impresiones/vistas
        nuevas_vistas = random.randint(150, 300)
        c.veces_publicado += nuevas_vistas
        
        # Logs divertidos de publicación
        canal_random = random.choice(plataformas_list).strip()
        logs.append(f"📸 [Agente IA] Publicando banner de {client_email} en la red *{canal_random}*.")
        logs.append(f"📈 [Agente IA] Se registraron +{nuevas_vistas} interacciones en la campaña de {client_email}.")
        
        if c.veces_publicado >= c.cantidad_vistas:
            c.veces_publicado = c.cantidad_vistas
            c.estado = "COMPLETADA"
            logs.append(f"✅ [Agente IA] ¡CAMPAÑA COMPLETADA! Se entregaron las {c.cantidad_vistas} vistas contratadas para {client_email}.")
        else:
            logs.append(f"📊 [Agente IA] Progreso de campaña de {client_email}: {c.veces_publicado}/{c.cantidad_vistas} impresiones.")
            
        db.add(c)
        
    db.commit()
    logs.append("🤖 [Agente IA] Procesamiento diario de publicidad completado con éxito.")
    return {"logs": logs}


from pydantic import BaseModel
from app.schemas import paciente as paciente_schemas

class MassEmailRequest(BaseModel):
    asunto: str
    cuerpo: str
    link_video: Optional[str] = None
    archivo_adjunto_url: Optional[str] = None

class MassAdRequest(BaseModel):
    plataformas: str
    mensaje: str
    link_video: Optional[str] = None
    archivo_adjunto_url: Optional[str] = None

class MassWhatsAppRequest(BaseModel):
    mensaje: str
    link_video: Optional[str] = None
    archivo_adjunto_url: Optional[str] = None

@router.get("/pacientes", response_model=List[paciente_schemas.PacienteResponse])
def get_pacientes_admin(
    current_admin: models.UsuarioSistema = Depends(deps.get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Retorna todos los pacientes/usuarios finales registrados con sus datos completos.
    """
    pacientes = db.query(models.Paciente).all()
    for p in pacientes:
        p.email = p.usuario.email if p.usuario else None
    return pacientes

@router.post("/correos-masivos")
def enviar_correos_masivos(
    req: MassEmailRequest,
    current_admin: models.UsuarioSistema = Depends(deps.get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Envía un correo electrónico masivo a todos los pacientes registrados y activos.
    """
    pacientes = db.query(models.Paciente).join(
        models.UsuarioSistema, models.Paciente.usuario_id == models.UsuarioSistema.id
    ).filter(
        models.UsuarioSistema.estado == models.EstadoUsuario.ACTIVO
    ).all()
    
    from app.services.email import send_email_notification
    enviados = 0
    for p in pacientes:
        try:
            extra_html = ""
            if req.link_video:
                extra_html += f'<p>🎥 <strong>Video de la campaña:</strong> <a href="{req.link_video}">{req.link_video}</a></p>'
            if req.archivo_adjunto_url:
                extra_html += f'<p>📎 <strong>Archivo adjunto:</strong> <a href="{req.archivo_adjunto_url}">Descargar Archivo</a></p>'
                
            send_email_notification(
                to_email=p.usuario.email,
                subject=req.asunto,
                body=f"<h2>{req.asunto}</h2><p>Estimado/a <strong>{p.nombres} {p.apellidos}</strong>,</p>{req.cuerpo}{extra_html}"
            )
            enviados += 1
        except Exception as e:
            print(f"Error enviando correo a {p.usuario.email}:", e)
            
    return {"message": f"Correo masivo enviado con éxito a {enviados} pacientes activos."}

@router.post("/publicidad-masiva")
def enviar_publicidad_masiva(
    req: MassAdRequest,
    current_admin: models.UsuarioSistema = Depends(deps.get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Simula el envío masivo de publicidad en redes sociales a los usuarios finales.
    """
    pacientes = db.query(models.Paciente).all()
    logs = [
        f"🤖 [Agente IA Admin] Iniciando campaña masiva de publicidad en redes: {req.plataformas}",
        f"📝 [Agente IA Admin] Mensaje promocional: '{req.mensaje}'"
    ]
    if req.link_video:
        logs.append(f"🎥 [Agente IA Admin] Video de la campaña: {req.link_video}")
    if req.archivo_adjunto_url:
        logs.append(f"📎 [Agente IA Admin] Archivo/Imagen adjunta: {req.archivo_adjunto_url}")
        
    for p in pacientes:
        logs.append(f"📲 [Agente IA Admin] Enviando anuncio a {p.nombres} ({p.usuario.email}) en {req.plataformas}.")
        
    return {"message": "Campaña masiva de publicidad procesada.", "logs": logs}

@router.post("/whatsapp-masivo")
def enviar_whatsapp_masivo(
    req: MassWhatsAppRequest,
    current_admin: models.UsuarioSistema = Depends(deps.get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Simula el envío masivo de mensajes de WhatsApp a los pacientes registrados y activos.
    """
    pacientes = db.query(models.Paciente).join(
        models.UsuarioSistema, models.Paciente.usuario_id == models.UsuarioSistema.id
    ).filter(
        models.UsuarioSistema.estado == models.EstadoUsuario.ACTIVO
    ).all()
    
    logs = [
        f"🤖 [WhatsApp Agent] Iniciando campaña masiva de WhatsApp...",
        f"💬 [WhatsApp Agent] Mensaje base: '{req.mensaje}'"
    ]
    if req.link_video:
        logs.append(f"🎥 [WhatsApp Agent] Enlace de video insertado: {req.link_video}")
    if req.archivo_adjunto_url:
        logs.append(f"📎 [WhatsApp Agent] Enlace de archivo adjunto: {req.archivo_adjunto_url}")
        
    enviados = 0
    for p in pacientes:
        phone = p.celular_whatsapp
        logs.append(f"🟢 [WhatsApp Agent] Enviando mensaje a {p.nombres} ({phone})")
        enviados += 1
        
    return {
        "message": f"Mensajes masivos de WhatsApp enviados con éxito a {enviados} pacientes activos.",
        "logs": logs
    }

@router.put("/proveedores/{proveedor_id}", response_model=proveedor_schemas.ProveedorResponse)
def update_proveedor(
    proveedor_id: str,
    prov_in: proveedor_schemas.ProveedorAdminUpdate,
    current_admin: models.UsuarioSistema = Depends(deps.get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Modifica todos los datos de un proveedor en el sistema.
    Accesible únicamente por el Administrador. Permite actualizar credenciales, estado, coordenadas y plan.
    """
    # 1. Buscar proveedor
    proveedor = db.query(models.ProveedorServicio).filter(
        models.ProveedorServicio.id == proveedor_id
    ).first()
    if not proveedor:
        raise HTTPException(
            status_code=404,
            detail="Proveedor no encontrado"
        )
        
    usuario = proveedor.usuario
    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuario del proveedor no encontrado"
        )

    # 2. Si se cambia el email, verificar unicidad
    if prov_in.email and prov_in.email != usuario.email:
        usuario_existente = db.query(models.UsuarioSistema).filter(
            models.UsuarioSistema.email == prov_in.email
        ).first()
        if usuario_existente:
            raise HTTPException(
                status_code=400,
                detail="Ya existe un usuario registrado con el correo electrónico proporcionado"
            )
        usuario.email = prov_in.email

    # 3. Si se cambia el RUC, verificar unicidad
    if prov_in.ruc_cedula and prov_in.ruc_cedula != proveedor.ruc_cedula:
        proveedor_existente = db.query(models.ProveedorServicio).filter(
            models.ProveedorServicio.ruc_cedula == prov_in.ruc_cedula
        ).first()
        if proveedor_existente:
            raise HTTPException(
                status_code=400,
                detail="Ya existe un proveedor registrado con este RUC/Cédula"
            )
        proveedor.ruc_cedula = prov_in.ruc_cedula

    # 4. Si se ingresa contraseña, encriptar y actualizar
    if prov_in.password:
        usuario.password_hash = deps.get_password_hash(prov_in.password)

    # 5. Actualizar los demás campos del proveedor
    if prov_in.nombre_comercial is not None:
        proveedor.nombre_comercial = prov_in.nombre_comercial
    if prov_in.celular_whatsapp is not None:
        proveedor.celular_whatsapp = prov_in.celular_whatsapp
    if prov_in.categoria is not None:
        proveedor.categoria = prov_in.categoria
    if prov_in.especialidad is not None:
        proveedor.especialidad = prov_in.especialidad
    if prov_in.latitud is not None:
        proveedor.latitud = prov_in.latitud
    if prov_in.longitud is not None:
        proveedor.longitud = prov_in.longitud
    if prov_in.precio_consulta is not None:
        proveedor.precio_consulta = prov_in.precio_consulta
    if prov_in.es_premium is not None:
        proveedor.es_premium = prov_in.es_premium
        # Ajustar membresía fija según plan
        proveedor.membresia_fija = Decimal("40.00") if prov_in.es_premium else Decimal("25.00")
    if prov_in.link_tiktok is not None:
        proveedor.link_tiktok = prov_in.link_tiktok
    if prov_in.link_instagram is not None:
        proveedor.link_instagram = prov_in.link_instagram
    if prov_in.link_facebook is not None:
        proveedor.link_facebook = prov_in.link_facebook
    if prov_in.ciudad is not None:
        proveedor.ciudad = prov_in.ciudad
        
    # Calcular sector dinámicamente si cambiaron coordenadas o ciudad
    from app.services.regions import get_sector_by_coordinates
    proveedor.sector = get_sector_by_coordinates(proveedor.latitud, proveedor.longitud, proveedor.ciudad)

    db.add(proveedor)
    db.add(usuario)
    db.commit()
    db.refresh(proveedor)
    
    # Mapear respuesta
    return proveedor_schemas.ProveedorResponse(
        id=proveedor.id,
        usuario_id=proveedor.usuario_id,
        ruc_cedula=proveedor.ruc_cedula,
        nombre_comercial=proveedor.nombre_comercial,
        celular_whatsapp=proveedor.celular_whatsapp,
        categoria=proveedor.categoria,
        especialidad=proveedor.especialidad,
        latitud=proveedor.latitud,
        longitud=proveedor.longitud,
        precio_consulta=proveedor.precio_consulta,
        imagen_url=proveedor.imagen_url,
        membresia_fija=proveedor.membresia_fija,
        es_premium=proveedor.es_premium,
        created_at=proveedor.created_at,
        email=usuario.email,
        estado=usuario.estado,
        link_tiktok=proveedor.link_tiktok,
        link_instagram=proveedor.link_instagram,
        link_facebook=proveedor.link_facebook,
        ciudad=proveedor.ciudad,
        sector=proveedor.sector
    )
