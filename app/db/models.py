import uuid
from datetime import datetime
import enum
from sqlalchemy import (
    Column,
    String,
    Float,
    Numeric,
    Boolean,
    DateTime,
    Date,
    Integer,
    ForeignKey,
    Enum as SQLEnum,
    JSON
)
from sqlalchemy.orm import relationship, backref
from app.db.database import Base

# 1. Definición de Enums de Python
class RolUsuario(str, enum.Enum):
    ADMIN = "ADMIN"
    PROVEEDOR = "PROVEEDOR"
    PACIENTE = "PACIENTE"

class EstadoUsuario(str, enum.Enum):
    ACTIVO = "ACTIVO"
    PENDIENTE_PAGO = "PENDIENTE_PAGO"
    BLOQUEADO = "BLOQUEADO"

class CanalAtribucion(str, enum.Enum):
    TIKTOK = "TikTok"
    INSTAGRAM = "Instagram"
    FACEBOOK = "Facebook"
    REFERIDO = "Referido Personal"

class CategoriaProveedor(str, enum.Enum):
    DOCTORES = "Doctores"
    SPAS = "Spas y Estética"
    CLINICAS = "Clínicas"
    FARMACIAS = "Farmacias"
    LABORATORIOS = "Laboratorios"

class EstadoFactura(str, enum.Enum):
    PAGADA = "PAGADA"
    PENDIENTE = "PENDIENTE"
    VENCIDA = "VENCIDA"

class EstadoCupon(str, enum.Enum):
    ACTIVO = "ACTIVO"
    REDIMIDO = "REDIMIDO"

class EstadoLeadCrm(str, enum.Enum):
    CONTACTADO = "CONTACTADO"
    AGENDADO = "AGENDADO"
    ATENDIDO = "ATENDIDO"
    NO_INTERESADO = "NO_INTERESADO"

# 2. Modelos ORM de SQLAlchemy
class UsuarioSistema(Base):
    __tablename__ = "usuarios_sistema"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True) # Null para pacientes sin contraseña
    rol = Column(SQLEnum(RolUsuario), nullable=False)
    estado = Column(SQLEnum(EstadoUsuario), default=EstadoUsuario.ACTIVO)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    paciente = relationship("Paciente", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    proveedor = relationship("ProveedorServicio", back_populates="usuario", uselist=False, cascade="all, delete-orphan")


class Paciente(Base):
    __tablename__ = "pacientes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id = Column(String(36), ForeignKey("usuarios_sistema.id", ondelete="CASCADE"), nullable=False)
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    cedula = Column(String(20), unique=True, nullable=False, index=True)
    celular_whatsapp = Column(String(20), nullable=False)
    origen_informacion = Column(SQLEnum(CanalAtribucion), nullable=False)
    cupon_descuento = Column(Numeric(10, 2), default=5.00) # Backward compatibility welcome coupon
    cupon_usado = Column(Boolean, default=False)
    referido_por_id = Column(String(36), ForeignKey("pacientes.id", ondelete="SET NULL"), nullable=True)
    link_tiktok = Column(String(255), nullable=True)
    link_instagram = Column(String(255), nullable=True)
    link_facebook = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    usuario = relationship("UsuarioSistema", back_populates="paciente")
    eventos_clic = relationship("EventoClicBilling", back_populates="paciente", cascade="all, delete-orphan")
    cupones = relationship("Cupon", back_populates="paciente", cascade="all, delete-orphan")
    resenas = relationship("Resena", back_populates="paciente", cascade="all, delete-orphan")
    
    # Relación jerárquica para referidos
    referido_por = relationship("Paciente", remote_side=[id], backref=backref("referidos", cascade="all, delete-orphan"))


class ProveedorServicio(Base):
    __tablename__ = "proveedores_servicio"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id = Column(String(36), ForeignKey("usuarios_sistema.id", ondelete="CASCADE"), nullable=False)
    ruc_cedula = Column(String(20), unique=True, nullable=False, index=True)
    nombre_comercial = Column(String(150), nullable=False)
    categoria = Column(SQLEnum(CategoriaProveedor), nullable=False, index=True)
    especialidad = Column(String(100), nullable=True)
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    precio_consulta = Column(Numeric(10, 2), nullable=False)
    imagen_url = Column(String(255), nullable=True)
    membresia_fija = Column(Numeric(10, 2), default=10.00)
    es_premium = Column(Boolean, default=False)
    link_tiktok = Column(String(255), nullable=True)
    link_instagram = Column(String(255), nullable=True)
    link_facebook = Column(String(255), nullable=True)
    ciudad = Column(String(100), nullable=True)
    sector = Column(String(100), nullable=True)
    celular_whatsapp = Column(String(20), nullable=True)
    servicios_adicionales = Column(JSON, nullable=True)
    google_calendar_link = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    usuario = relationship("UsuarioSistema", back_populates="proveedor")
    eventos_clic = relationship("EventoClicBilling", back_populates="proveedor", cascade="all, delete-orphan")
    facturas = relationship("Factura", back_populates="proveedor", cascade="all, delete-orphan")
    campanas = relationship("CampanaDescuento", back_populates="proveedor", cascade="all, delete-orphan")
    resenas = relationship("Resena", back_populates="proveedor", cascade="all, delete-orphan")
    cupones_redimidos = relationship("Cupon", back_populates="proveedor_redencion")
    configuracion_agenda = relationship("ConfiguracionAgendaProveedor", back_populates="proveedor", uselist=False, cascade="all, delete-orphan")
    citas = relationship("CitaProveedor", back_populates="proveedor", cascade="all, delete-orphan")


class EventoClicBilling(Base):
    __tablename__ = "eventos_clic_billing"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    proveedor_id = Column(String(36), ForeignKey("proveedores_servicio.id", ondelete="CASCADE"), nullable=False, index=True)
    paciente_id = Column(String(36), ForeignKey("pacientes.id", ondelete="SET NULL"), nullable=True)
    estado_lead = Column(SQLEnum(EstadoLeadCrm), default=EstadoLeadCrm.CONTACTADO)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relaciones
    proveedor = relationship("ProveedorServicio", back_populates="eventos_clic")
    paciente = relationship("Paciente", back_populates="eventos_clic")


class Factura(Base):
    __tablename__ = "facturas"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    proveedor_id = Column(String(36), ForeignKey("proveedores_servicio.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha_emision = Column(Date, default=lambda: datetime.utcnow().date())
    fecha_vencimiento = Column(Date, nullable=False)
    monto_fijo = Column(Numeric(10, 2), default=10.00)
    monto_clics = Column(Numeric(10, 2), default=0.00)
    monto_publicidad = Column(Numeric(10, 2), default=0.00)
    monto_total = Column(Numeric(10, 2), nullable=False)
    estado = Column(SQLEnum(EstadoFactura), default=EstadoFactura.PENDIENTE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    proveedor = relationship("ProveedorServicio", back_populates="facturas")


class CampanaDescuento(Base):
    __tablename__ = "campanas_descuento"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    proveedor_id = Column(String(36), ForeignKey("proveedores_servicio.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    monto = Column(Numeric(10, 2), default=5.00)
    limite_usos = Column(Integer, default=100)
    usos_actuales = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    proveedor = relationship("ProveedorServicio", back_populates="campanas")
    cupones = relationship("Cupon", back_populates="campana")


class Cupon(Base):
    __tablename__ = "cupones"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    paciente_id = Column(String(36), ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    monto = Column(Numeric(10, 2), default=5.00)
    estado = Column(SQLEnum(EstadoCupon), default=EstadoCupon.ACTIVO)
    proveedor_redencion_id = Column(String(36), ForeignKey("proveedores_servicio.id", ondelete="SET NULL"), nullable=True)
    campana_id = Column(String(36), ForeignKey("campanas_descuento.id", ondelete="SET NULL"), nullable=True)
    fecha_redencion = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    paciente = relationship("Paciente", back_populates="cupones")
    proveedor_redencion = relationship("ProveedorServicio", back_populates="cupones_redimidos")
    campana = relationship("CampanaDescuento", back_populates="cupones")


class Resena(Base):
    __tablename__ = "resenas"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    proveedor_id = Column(String(36), ForeignKey("proveedores_servicio.id", ondelete="CASCADE"), nullable=False, index=True)
    paciente_id = Column(String(36), ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False, index=True)
    calificacion = Column(Integer, nullable=False) # 1 a 5
    comentario = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    proveedor = relationship("ProveedorServicio", back_populates="resenas")
    paciente = relationship("Paciente", back_populates="resenas")


class SolicitudPublicidad(Base):
    __tablename__ = "solicitudes_publicidad"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id = Column(String(36), ForeignKey("usuarios_sistema.id", ondelete="CASCADE"), nullable=False)
    plataformas = Column(String(100), nullable=False)
    cantidad_vistas = Column(Integer, nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    estado = Column(String(50), default="PENDIENTE")
    veces_publicado = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    usuario = relationship("UsuarioSistema")


class CodigoVerificacion(Base):
    __tablename__ = "codigos_verificacion"
    
    id = Column(Integer, primary_key=True, index=True)
    destino = Column(String(100), nullable=False, index=True) # Correo o Teléfono
    codigo = Column(String(6), nullable=False)
    expira_at = Column(DateTime, nullable=False)
    usado = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConfiguracionAgendaProveedor(Base):
    __tablename__ = "configuracion_agenda_proveedores"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    proveedor_id = Column(String(36), ForeignKey("proveedores_servicio.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    horarios_disponibilidad = Column(JSON, nullable=True) # e.g. {"lunes": ["08:00", "17:00"], "martes": ["08:00", "17:00"], ...}
    duracion_turno = Column(Integer, default=30) # en minutos
    respuesta_automatica = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    proveedor = relationship("ProveedorServicio", back_populates="configuracion_agenda")


class CitaProveedor(Base):
    __tablename__ = "citas_proveedores"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    proveedor_id = Column(String(36), ForeignKey("proveedores_servicio.id", ondelete="CASCADE"), nullable=False, index=True)
    paciente_id = Column(String(36), ForeignKey("pacientes.id", ondelete="SET NULL"), nullable=True, index=True)
    paciente_nombre = Column(String(150), nullable=False) # Nombre completo del paciente o asunto del bloqueo
    fecha = Column(String(10), nullable=False) # Formato YYYY-MM-DD
    hora_inicio = Column(String(5), nullable=False) # Formato HH:MM
    hora_fin = Column(String(5), nullable=False) # Formato HH:MM
    estado = Column(String(50), default="RESERVADA") # RESERVADA, BLOQUEADA
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    proveedor = relationship("ProveedorServicio", back_populates="citas")
    paciente = relationship("Paciente")

    @property
    def paciente_celular(self):
        return self.paciente.celular_whatsapp if self.paciente else None
