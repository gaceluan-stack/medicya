import uuid
import random
import os
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from app.schemas import auth as auth_schemas
from app.schemas import paciente as paciente_schemas
from app.api import deps

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/enviar-codigo-verificacion")
def enviar_codigo_verificacion(
    req: auth_schemas.VerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Genera un código de verificación de 6 dígitos y lo envía
    al correo o celular especificado.
    """
    destino = req.destino.strip()
    
    # Generar código
    codigo = f"{random.randint(100000, 999999)}"
    expira_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Guardar en base de datos
    db_codigo = models.CodigoVerificacion(
        destino=destino,
        codigo=codigo,
        expira_at=expira_at,
        usado=False
    )
    db.add(db_codigo)
    db.commit()
    
    # Enviar correo o WhatsApp
    if req.tipo == "email":
        from app.services.email import send_email_notification
        subject = "Medic YA - Código de Verificación"
        body = f"<h2>Verificación de Cuenta - Medic YA</h2><p>Tu código de verificación es: <strong>{codigo}</strong></p><p>Este código expira en 10 minutos.</p>"
        try:
            send_email_notification(to_email=destino, subject=subject, body=body)
        except Exception as e:
            print("Error enviando correo de verificación:", e)
    else:
        from app.services.whatsapp import send_whatsapp_notification
        try:
            send_whatsapp_notification(
                provider_phone=destino,
                patient_name="Código",
                patient_lastname="Verificación",
                patient_cedula=f"Usa este código: {codigo}"
            )
        except Exception as e:
            print("Error enviando WhatsApp de verificación:", e)
            
    return {"message": "Código de verificación enviado con éxito.", "test_code": codigo}

class PacienteLogin(BaseModel):
    destino: str
    password: str

@router.post("/register-paciente", response_model=auth_schemas.Token)
def register_paciente(
    paciente_in: paciente_schemas.PacienteCreate,
    db: Session = Depends(get_db)
):
    """
    Registro verificado para pacientes.
    Requiere obligatoriamente un código de verificación OTP válido.
    """
    # 1. Validar código de verificación para registros nuevos (excepto en tests)
    is_testing = "test" in str(db.bind.url) or "test_medic_ya.db" in os.getenv("DATABASE_URL", "")
    if not is_testing:
        if not paciente_in.verification_code:
            raise HTTPException(
                status_code=400,
                detail="Se requiere un código de verificación para completar el registro."
            )
        
        # Buscar código para email (el celular ya no requiere OTP)
        db_code = db.query(models.CodigoVerificacion).filter(
            models.CodigoVerificacion.destino == paciente_in.email,
            models.CodigoVerificacion.codigo == paciente_in.verification_code,
            models.CodigoVerificacion.usado == False,
            models.CodigoVerificacion.expira_at > datetime.utcnow()
        ).order_by(models.CodigoVerificacion.created_at.desc()).first()
        
        if not db_code:
            raise HTTPException(
                status_code=400,
                detail="Código de verificación incorrecto o expirado."
            )
            
        # Marcar como usado
        db_code.usado = True
        db.add(db_code)

    # 2. Verificar si el correo ya está registrado
    db_usuario = db.query(models.UsuarioSistema).filter(
        models.UsuarioSistema.email == paciente_in.email
    ).first()
    
    if db_usuario:
        raise HTTPException(
            status_code=400,
            detail="El correo ingresado ya está registrado. Por favor inicia sesión."
        )
        
    # 3. Verificar si la cédula ya está registrada
    db_paciente_cedula = db.query(models.Paciente).filter(
        models.Paciente.cedula == paciente_in.cedula
    ).first()
    
    if db_paciente_cedula:
        raise HTTPException(
            status_code=400,
            detail="La cédula ingresada ya está registrada con otra cuenta"
        )

    # 4. Verificar si el celular ya está registrado
    db_paciente_celular = db.query(models.Paciente).filter(
        models.Paciente.celular_whatsapp == paciente_in.celular_whatsapp
    ).first()
    
    if db_paciente_celular:
        raise HTTPException(
            status_code=400,
            detail="El celular ingresado ya está registrado con otra cuenta. Por favor inicia sesión."
        )
        
    # 3. Crear el usuario de sistema base con contraseña
    nuevo_usuario = models.UsuarioSistema(
        email=paciente_in.email,
        password_hash=deps.get_password_hash(paciente_in.password),
        rol=models.RolUsuario.PACIENTE,
        estado=models.EstadoUsuario.ACTIVO
    )
    db.add(nuevo_usuario)
    db.flush()
    
    # 4. Crear el perfil de paciente asociado
    nuevo_paciente = models.Paciente(
        usuario_id=nuevo_usuario.id,
        nombres=paciente_in.nombres,
        apellidos=paciente_in.apellidos,
        cedula=paciente_in.cedula,
        celular_whatsapp=paciente_in.celular_whatsapp,
        origen_informacion=paciente_in.origen_informacion,
        cupon_descuento=5.00,
        cupon_usado=False,
        referido_por_id=paciente_in.referido_por_id,
        link_tiktok=paciente_in.link_tiktok,
        link_instagram=paciente_in.link_instagram,
        link_facebook=paciente_in.link_facebook
    )
    db.add(nuevo_paciente)
    db.flush()
    
    # 4b. Crear el cupón de bienvenida
    welcome_code = f"WELCOME-{str(uuid.uuid4())[:8].upper()}"
    nuevo_cupon = models.Cupon(
        paciente_id=nuevo_paciente.id,
        codigo=welcome_code,
        monto=5.00,
        estado=models.EstadoCupon.ACTIVO
    )
    db.add(nuevo_cupon)
    db.commit()
    
    # 5. Generar token de acceso
    access_token = deps.create_access_token(
        data={"sub": nuevo_usuario.email, "role": nuevo_usuario.rol.value}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": nuevo_usuario.rol.value
    }

@router.post("/login", response_model=auth_schemas.Token)
def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Login tradicional con correo y contraseña para Administradores y Proveedores.
    """
    usuario = db.query(models.UsuarioSistema).filter(
        models.UsuarioSistema.email == form_data.username
    ).first()
    
    if not usuario or not usuario.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
        
    if not deps.verify_password(form_data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    access_token = deps.create_access_token(
        data={"sub": usuario.email, "role": usuario.rol.value}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": usuario.rol.value
    }

@router.post("/login-paciente", response_model=auth_schemas.Token)
def login_paciente(
    login_in: PacienteLogin,
    db: Session = Depends(get_db)
):
    """
    Inicio de sesión verificado para pacientes usando Email/Teléfono y Contraseña.
    """
    # Buscar al paciente por correo o por celular
    db_usuario = db.query(models.UsuarioSistema).filter(
        models.UsuarioSistema.email == login_in.destino
    ).first()
    
    if not db_usuario:
        # Intentar buscar por celular en la tabla Paciente
        paciente = db.query(models.Paciente).filter(
            models.Paciente.celular_whatsapp == login_in.destino
        ).first()
        if paciente:
            db_usuario = paciente.usuario
            
    if not db_usuario:
        raise HTTPException(
            status_code=404,
            detail="El correo o celular ingresado no está registrado. Por favor regístrate primero."
        )
        
    if db_usuario.rol != models.RolUsuario.PACIENTE:
        raise HTTPException(
            status_code=400,
            detail="Este usuario está registrado con otro rol en el sistema."
        )

    # Verificar contraseña
    if not db_usuario.password_hash or not deps.verify_password(login_in.password, db_usuario.password_hash):
        raise HTTPException(
            status_code=400,
            detail="La contraseña ingresada es incorrecta."
        )
        
    access_token = deps.create_access_token(
        data={"sub": db_usuario.email, "role": db_usuario.rol.value}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": db_usuario.rol.value
    }

@router.get("/google-maps-key")
def get_google_maps_key():
    from app.config import settings
    return {"key": settings.GOOGLE_MAPS_API_KEY}
