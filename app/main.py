import os
from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.database import engine, Base
from app.api import auth, pacientes, proveedores, admin, billing

# Crear tablas si no existen (ideal para SQLite local)
Base.metadata.create_all(bind=engine)

# Migración rápida: agregar columna monto_publicidad a la tabla facturas si no existe
try:
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE facturas ADD COLUMN monto_publicidad NUMERIC(10, 2) DEFAULT 0.00;"))
        print("Migración: Columna 'monto_publicidad' agregada a la tabla 'facturas'")
except Exception as e:
    # Ignorar si ya existe
    pass

# Migraciones de redes sociales y clasificación para proveedores y pacientes
try:
    from sqlalchemy import text
    
    # Redes sociales para proveedores
    for col in ["link_tiktok", "link_instagram", "link_facebook"]:
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE proveedores_servicio ADD COLUMN {col} VARCHAR(255);"))
        except Exception:
            pass
    
    # Redes sociales para pacientes
    for col in ["link_tiktok", "link_instagram", "link_facebook"]:
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE pacientes ADD COLUMN {col} VARCHAR(255);"))
        except Exception:
            pass
    
    # Ciudad, Sector, Celular y Servicios para proveedores
    for col, col_type in [("ciudad", "VARCHAR(100)"), ("sector", "VARCHAR(100)"), ("celular_whatsapp", "VARCHAR(20) DEFAULT '593987654321'"), ("servicios_adicionales", "JSON")]:
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE proveedores_servicio ADD COLUMN {col} {col_type};"))
        except Exception:
            pass
except Exception as e:
    print("Error general en migraciones:", e)

# Auto-clasificar proveedores existentes sin ciudad/sector
try:
    from app.db.database import SessionLocal
    from app.db import models
    from app.services.sector_classifier import classify_location
    db = SessionLocal()
    unclassified = db.query(models.ProveedorServicio).filter(
        (models.ProveedorServicio.ciudad == None) | (models.ProveedorServicio.sector == None)
    ).all()
    if unclassified:
        for p in unclassified:
            ciudad, sector = classify_location(p.latitud, p.longitud)
            p.ciudad = ciudad
            p.sector = sector
            print(f"Auto-clasificado: {p.nombre_comercial} -> {ciudad}, {sector}")
        db.commit()
    db.close()
except Exception as e:
    print("Error auto-clasificando proveedores:", e)

# Auto-formatear números de WhatsApp de proveedores existentes
try:
    from app.db.database import SessionLocal
    from app.db import models
    from app.services.phone_formatter import format_ecuador_whatsapp
    db = SessionLocal()
    proveedores_list = db.query(models.ProveedorServicio).all()
    for p in proveedores_list:
        if p.celular_whatsapp:
            formatted = format_ecuador_whatsapp(p.celular_whatsapp)
            if p.celular_whatsapp != formatted:
                print(f"Formateando teléfono de {p.nombre_comercial}: {p.celular_whatsapp} -> {formatted}")
                p.celular_whatsapp = formatted
    db.commit()
    db.close()
except Exception as e:
    print("Error formateando teléfonos de proveedores existentes:", e)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API y PWA para conectar pacientes con profesionales de la salud",
    version="1.0.0"
)

# Configurar middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Configurar directorios para plantillas e interfaces estáticas
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
static_dir = os.path.join(templates_dir, "static")

# Asegurar que existan los directorios
os.makedirs(static_dir, exist_ok=True)

# Montar los archivos estáticos
app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=templates_dir)
templates.env.cache = None

# 2. Rutas del Servidor de Plantillas (Frontend PWA)
@app.get("/", response_class=HTMLResponse)
def index_map(request: Request):
    """Vista principal: Mapa interactivo con Leaflet.js para los pacientes."""
    return templates.TemplateResponse(request, "index.html")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Vista de login para Administradores y Proveedores."""
    return templates.TemplateResponse(request, "login.html")

@app.get("/dashboard/proveedor", response_class=HTMLResponse)
def provider_dashboard(request: Request):
    """Vista del panel de métricas en tiempo real para Proveedores."""
    return templates.TemplateResponse(request, "dashboard_prov.html")

@app.get("/dashboard/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    """Vista del panel de control global para el Administrador."""
    return templates.TemplateResponse(request, "dashboard_admin.html")

# 3. Incluir enrutadores de la API REST
app.include_router(auth.router, prefix="/api")
app.include_router(pacientes.router, prefix="/api")
app.include_router(proveedores.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(billing.router, prefix="/api")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}
