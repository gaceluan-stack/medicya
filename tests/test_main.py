import os
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configurar variables de entorno para usar una base de datos SQLite de prueba en memoria
os.environ["DATABASE_URL"] = "sqlite:///./test_medic_ya.db"

from app.main import app
from app.db.database import Base, get_db
from app.db import models
from app.api import deps
from app.services import billing_cron

# Configurar motor de base de datos SQLite para pruebas
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_medic_ya.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Reemplazar la dependencia de BD en FastAPI
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    # Crear tablas limpias para cada test
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Crear un Administrador por defecto para las pruebas
    admin_hash = deps.get_password_hash("admin123")
    admin_user = models.UsuarioSistema(
        email="admin@medicya.com",
        password_hash=admin_hash,
        rol=models.RolUsuario.ADMIN,
        estado=models.EstadoUsuario.ACTIVO
    )
    db.add(admin_user)
    db.commit()
    db.close()
    
    yield
    
    # Eliminar tablas después de las pruebas
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_medic_ya.db"):
        try:
            os.remove("./test_medic_ya.db")
        except PermissionError:
            pass

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_paciente_registro_y_login_passwordless():
    # 1. Registrar paciente por primera vez
    paciente_data = {
        "email": "paciente@test.com",
        "password": "pacientepassword",
        "nombres": "Juan",
        "apellidos": "Pérez",
        "cedula": "1712345678",
        "celular_whatsapp": "+593987654321",
        "origen_informacion": "TikTok"
    }
    
    response = client.post("/api/auth/register-paciente", json=paciente_data)
    assert response.status_code == 200
    res_data = response.json()
    assert "access_token" in res_data
    assert res_data["role"] == "PACIENTE"
    
    # Verificar cupón de $5 USD y datos del perfil
    token = res_data["access_token"]
    profile_response = client.get("/api/pacientes/me", headers={"Authorization": f"Bearer {token}"})
    assert profile_response.status_code == 200
    prof_data = profile_response.json()
    assert prof_data["nombres"] == "Juan"
    assert float(prof_data["cupon_descuento"]) == 5.00
    assert prof_data["cupon_usado"] is False

    # 2. Registrar de nuevo con el mismo correo (Debe fallar indicando que ya existe)
    response_login = client.post("/api/auth/register-paciente", json=paciente_data)
    assert response_login.status_code == 400
    assert "ya está registrado" in response_login.json()["detail"]

    # 3. Iniciar sesión a través del nuevo endpoint login-paciente (con usuario y contraseña)
    login_payload = {
        "destino": "paciente@test.com",
        "password": "pacientepassword"
    }
    response_login_endpoint = client.post("/api/auth/login-paciente", json=login_payload)
    assert response_login_endpoint.status_code == 200
    assert "access_token" in response_login_endpoint.json()

def test_admin_crea_proveedor_y_contacto_paciente():
    # 1. Login de Administrador
    login_data = {
        "username": "admin@medicya.com",
        "password": "admin123"
    }
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == 200
    admin_token = response.json()["access_token"]
    
    # 2. Crear Proveedor (Doctor)
    proveedor_payload = {
        "email": "doctor@medicya.com",
        "password": "doctorpassword",
        "ruc_cedula": "1711223344001",
        "nombre_comercial": "Clínica del Doctor Carlos",
        "categoria": "Doctores",
        "especialidad": "Cardiólogo",
        "latitud": -0.180653,
        "longitud": -78.467834,
        "precio_consulta": 45.00,
        "membresia_fija": 10.00
    }
    
    response_prov = client.post(
        "/api/admin/proveedores",
        json=proveedor_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response_prov.status_code == 201
    prov_data = response_prov.json()
    prov_id = prov_data["id"]
    assert prov_data["nombre_comercial"] == "Clínica del Doctor Carlos"
    
    # 3. Comprobar que aparece en el mapa público
    response_map = client.get("/api/proveedores/mapa")
    assert response_map.status_code == 200
    map_provs = response_map.json()
    assert len(map_provs) == 1
    assert map_provs[0]["id"] == prov_id

    # 4. Registrar un Paciente
    paciente_payload = {
        "email": "paciente_interesado@test.com",
        "password": "pacientepassword",
        "nombres": "María",
        "apellidos": "Gómez",
        "cedula": "1788776655",
        "celular_whatsapp": "+593980000000",
        "origen_informacion": "Instagram"
    }
    response_pac = client.post("/api/auth/register-paciente", json=paciente_payload)
    pac_token = response_pac.json()["access_token"]

    # 5. Paciente hace click en "Contactar"
    response_contact = client.post(
        f"/api/proveedores/{prov_id}/contactar",
        headers={"Authorization": f"Bearer {pac_token}"}
    )
    assert response_contact.status_code == 201
    assert "Contacto registrado exitosamente" in response_contact.json()["message"]

    # 6. Login del Doctor para ver su panel de métricas
    login_doctor = {
        "username": "doctor@medicya.com",
        "password": "doctorpassword"
    }
    response_doc_login = client.post("/api/auth/login", data=login_doctor)
    doc_token = response_doc_login.json()["access_token"]
    
    # Obtener métricas
    response_metrics = client.get(
        "/api/proveedores/dashboard/metricas",
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    assert response_metrics.status_code == 200
    metrics = response_metrics.json()
    assert metrics["clics_recibidos"] == 1
    assert metrics["prospectos_generados"] == 1
    assert metrics["lista_prospectos"][0]["nombres"] == "María"

def test_cron_jobs_facturacion_y_bloqueo_por_mora():
    db = TestingSessionLocal()
    
    # 1. Sembrar Proveedor
    user_prov = models.UsuarioSistema(
        email="spa@medicya.com",
        password_hash=deps.get_password_hash("spapassword"),
        rol=models.RolUsuario.PROVEEDOR,
        estado=models.EstadoUsuario.ACTIVO
    )
    db.add(user_prov)
    db.flush()
    
    prov = models.ProveedorServicio(
        usuario_id=user_prov.id,
        ruc_cedula="1799887766001",
        nombre_comercial="Spa Sentirse Bien",
        categoria=models.CategoriaProveedor.SPAS,
        latitud=-0.20,
        longitud=-78.50,
        precio_consulta=25.00,
        membresia_fija=10.00
    )
    db.add(prov)
    db.flush()
    
    # 2. Agregar 1500 clics de prueba
    for i in range(1500):
        clic = models.EventoClicBilling(proveedor_id=prov.id, paciente_id=None)
        db.add(clic)
    db.commit()
    
    # 3. Ejecutar cron de facturación mensual
    billing_cron.run_monthly_billing(db)
    
    # Comprobar factura generada: Membresía Fija ($10) + Clics (1500 clics -> 1 bloque de 1000 = $5 adicionales) = $15.00
    factura = db.query(models.Factura).filter(models.Factura.proveedor_id == prov.id).first()
    assert factura is not None
    assert float(factura.monto_fijo) == 10.00
    assert float(factura.monto_clics) == 5.00
    assert float(factura.monto_total) == 15.00
    assert factura.estado == models.EstadoFactura.PENDIENTE
    
    # El proveedor debe haber pasado a PENDIENTE_PAGO
    db.refresh(user_prov)
    assert user_prov.estado == models.EstadoUsuario.PENDIENTE_PAGO
    
    # 4. Simular factura vencida (adelantar vencimiento a hace 5 días)
    factura.fecha_vencimiento = datetime.utcnow().date() - timedelta(days=5)
    db.add(factura)
    db.commit()
    
    # Ejecutar cron de revisión diaria de mora
    billing_cron.run_daily_overdue_check(db)
    
    # Cuenta debe ser BLOQUEADA y factura marcada como VENCIDA
    db.refresh(user_prov)
    db.refresh(factura)
    assert user_prov.estado == models.EstadoUsuario.BLOQUEADO
    assert factura.estado == models.EstadoFactura.VENCIDA
    
    # Comprobar que no sale en el mapa público ya que está bloqueado
    response_map = client.get("/api/proveedores/mapa")
    assert len(response_map.json()) == 0
    
    # 5. Pagar factura vencida para restaurar la cuenta
    # Login de Proveedor
    login_prov = {
        "username": "spa@medicya.com",
        "password": "spapassword"
    }
    prov_token = client.post("/api/auth/login", data=login_prov).json()["access_token"]
    
    # POST pagar factura
    response_pay = client.post(
        f"/api/billing/facturas/{factura.id}/pagar",
        headers={"Authorization": f"Bearer {prov_token}"}
    )
    assert response_pay.status_code == 200
    assert response_pay.json()["estado_cuenta_proveedor"] == "ACTIVO"
    
    # Comprobar que ahora vuelve a aparecer en el mapa público
    response_map_post = client.get("/api/proveedores/mapa")
    assert len(response_map_post.json()) == 1
    
    db.close()

def test_referral_rewards():
    # 1. Registrar Paciente A (Patrocinador)
    pac_a_data = {
        "email": "patrocinador@test.com",
        "password": "pacientepassword",
        "nombres": "Pedro",
        "apellidos": "Sánchez",
        "cedula": "1711111111",
        "celular_whatsapp": "+593981111111",
        "origen_informacion": "TikTok"
    }
    res_a = client.post("/api/auth/register-paciente", json=pac_a_data)
    token_a = res_a.json()["access_token"]
    
    # Obtener ID de Paciente A
    prof_a = client.get("/api/pacientes/me", headers={"Authorization": f"Bearer {token_a}"}).json()
    id_a = prof_a["id"]
    
    # 2. Registrar Paciente B (Referido por A)
    pac_b_data = {
        "email": "referido@test.com",
        "password": "pacientepassword",
        "nombres": "Gabriel",
        "apellidos": "Torres",
        "cedula": "1722222222",
        "celular_whatsapp": "+593982222222",
        "origen_informacion": "Referido Personal",
        "referido_por_id": id_a
    }
    res_b = client.post("/api/auth/register-paciente", json=pac_b_data)
    token_b = res_b.json()["access_token"]
    
    # Obtener billetera de B y su cupón de bienvenida
    wallet_b = client.get("/api/pacientes/me/cupones", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert len(wallet_b) == 1
    welcome_coupon_code = wallet_b[0]["codigo"]
    assert welcome_coupon_code.startswith("WELCOME-")
    
    # 3. Crear doctor e iniciar sesión para quemar el cupón
    login_admin = client.post("/api/auth/login", data={"username": "admin@medicya.com", "password": "admin123"})
    admin_token = login_admin.json()["access_token"]
    
    doctor_payload = {
        "email": "doctor_ref@medicya.com",
        "password": "doctorpassword",
        "ruc_cedula": "1722334455001",
        "nombre_comercial": "Consultorio Referido",
        "categoria": "Doctores",
        "especialidad": "Dermatólogo",
        "latitud": -0.19,
        "longitud": -78.48,
        "precio_consulta": 40.00,
        "membresia_fija": 10.00
    }
    client.post("/api/admin/proveedores", json=doctor_payload, headers={"Authorization": f"Bearer {admin_token}"})
    
    login_doctor = client.post("/api/auth/login", data={"username": "doctor_ref@medicya.com", "password": "doctorpassword"})
    doc_token = login_doctor.json()["access_token"]
    
    # Redimir el cupón de bienvenida del paciente referido B
    res_burn = client.post(
        f"/api/proveedores/redimir-cupon?codigo={welcome_coupon_code}",
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    assert res_burn.status_code == 200
    
    # 4. Ambos deben haber ganado $5 adicionales
    wallet_a_post = client.get("/api/pacientes/me/cupones", headers={"Authorization": f"Bearer {token_a}"}).json()
    # A debería tener el de bienvenida y el cupón REF-
    assert len(wallet_a_post) == 2
    assert any(c["codigo"].startswith("REF-") for c in wallet_a_post)
    assert any(float(c["monto"]) == 5.00 for c in wallet_a_post)
    
    wallet_b_post = client.get("/api/pacientes/me/cupones", headers={"Authorization": f"Bearer {token_b}"}).json()
    # B debería tener el de bienvenida (REDIMIDO) y el premio (ACTIVO)
    assert len(wallet_b_post) == 2
    assert any(c["estado"] == "REDIMIDO" for c in wallet_b_post)
    assert any(c["codigo"].startswith("REWARD-") and c["estado"] == "ACTIVO" for c in wallet_b_post)

def test_premium_campaign_and_redemption():
    # 1. Crear Doctor Premium vía Admin
    login_admin = client.post("/api/auth/login", data={"username": "admin@medicya.com", "password": "admin123"})
    admin_token = login_admin.json()["access_token"]
    
    doctor_premium_payload = {
        "email": "premium_doc@medicya.com",
        "password": "premiumpassword",
        "ruc_cedula": "1755667788001",
        "nombre_comercial": "Centro Médico Premium",
        "categoria": "Doctores",
        "especialidad": "Pediatra",
        "latitud": -0.195,
        "longitud": -78.475,
        "precio_consulta": 60.00,
        "membresia_fija": 10.00,
        "es_premium": True # Premium Flag
    }
    client.post("/api/admin/proveedores", json=doctor_premium_payload, headers={"Authorization": f"Bearer {admin_token}"})
    
    # 2. Login Doctor Premium
    login_doc = client.post("/api/auth/login", data={"username": "premium_doc@medicya.com", "password": "premiumpassword"})
    doc_token = login_doc.json()["access_token"]
    
    # Crear campaña de descuento propia
    camp_payload = {
        "codigo": "SUPERDOC",
        "monto": 7.00,
        "limite_usos": 50
    }
    res_camp = client.post("/api/proveedores/campanas", json=camp_payload, headers={"Authorization": f"Bearer {doc_token}"})
    assert res_camp.status_code == 201
    assert res_camp.json()["codigo"] == "SUPERDOC"
    
    # 3. Paciente canjea campaña
    pac_data = {
        "email": "paciente_camp@test.com",
        "password": "pacientepassword",
        "nombres": "Lucía",
        "apellidos": "Vargas",
        "cedula": "1733333333",
        "celular_whatsapp": "+593983333333",
        "origen_informacion": "Facebook"
    }
    res_pac = client.post("/api/auth/register-paciente", json=pac_data)
    pac_token = res_pac.json()["access_token"]
    
    # Canjear campaña SUPERDOC
    res_claim = client.post(
        f"/api/proveedores/canjear-campana?codigo_campana=SUPERDOC",
        headers={"Authorization": f"Bearer {pac_token}"}
    )
    assert res_claim.status_code == 201
    cupon_claim_code = res_claim.json()["cupon"]
    assert cupon_claim_code.startswith("CAMP-SUPERDOC-")
    
    # 4. Doctor Premium redime el cupón
    res_burn_camp = client.post(
        f"/api/proveedores/redimir-cupon?codigo={cupon_claim_code}",
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    assert res_burn_camp.status_code == 200
    assert float(res_burn_camp.json()["monto_descuento"]) == 7.00

def test_verified_reviews():
    # 1. Crear doctor y paciente
    login_admin = client.post("/api/auth/login", data={"username": "admin@medicya.com", "password": "admin123"})
    admin_token = login_admin.json()["access_token"]
    
    doctor_payload = {
        "email": "doctor_rev@medicya.com",
        "password": "doctorpassword",
        "ruc_cedula": "1788990011001",
        "nombre_comercial": "Consultorio Reseñas",
        "categoria": "Doctores",
        "especialidad": "Cardiólogo",
        "latitud": -0.17,
        "longitud": -78.49,
        "precio_consulta": 50.00,
        "membresia_fija": 10.00
    }
    res_doc = client.post("/api/admin/proveedores", json=doctor_payload, headers={"Authorization": f"Bearer {admin_token}"})
    doc_id = res_doc.json()["id"]
    
    pac_data = {
        "email": "paciente_rev@test.com",
        "password": "pacientepassword",
        "nombres": "Roberto",
        "apellidos": "Lara",
        "cedula": "1744444444",
        "celular_whatsapp": "+593984444444",
        "origen_informacion": "Instagram"
    }
    res_pac = client.post("/api/auth/register-paciente", json=pac_data)
    pac_token = res_pac.json()["access_token"]
    
    # 2. Intentar dejar reseña sin haber sido atendido -> Falla 403
    res_rev_fail = client.post(
        f"/api/proveedores/{doc_id}/resenas",
        json={"calificacion": 5, "comentario": "Excelente médico"},
        headers={"Authorization": f"Bearer {pac_token}"}
    )
    assert res_rev_fail.status_code == 403
    assert "Solo puedes escribir una reseña" in res_rev_fail.json()["detail"]
    
    # 3. Simular atención redimiendo cupón de bienvenida
    wallet = client.get("/api/pacientes/me/cupones", headers={"Authorization": f"Bearer {pac_token}"}).json()
    welcome_code = wallet[0]["codigo"]
    
    login_doc = client.post("/api/auth/login", data={"username": "doctor_rev@medicya.com", "password": "doctorpassword"})
    doc_token = login_doc.json()["access_token"]
    
    client.post(f"/api/proveedores/redimir-cupon?codigo={welcome_code}", headers={"Authorization": f"Bearer {doc_token}"})
    
    # 4. Dejar reseña con cupón REDIMIDO -> Éxito
    res_rev_success = client.post(
        f"/api/proveedores/{doc_id}/resenas",
        json={"calificacion": 4, "comentario": "Atención rápida y amable"},
        headers={"Authorization": f"Bearer {pac_token}"}
    )
    assert res_rev_success.status_code == 201
    
    # 5. Consultar reseñas del doctor
    reviews_list = client.get(f"/api/proveedores/{doc_id}/resenas").json()
    assert len(reviews_list) == 1
    assert reviews_list[0]["calificacion"] == 4
    assert reviews_list[0]["comentario"] == "Atención rápida y amable"
    assert reviews_list[0]["paciente_nombre"] == "Roberto L." # Apellido ofuscado

def test_crm_prospect_update():
    # 1. Crear Doctor y Paciente
    login_admin = client.post("/api/auth/login", data={"username": "admin@medicya.com", "password": "admin123"})
    admin_token = login_admin.json()["access_token"]
    
    doctor_payload = {
        "email": "doctor_crm@medicya.com",
        "password": "doctorpassword",
        "ruc_cedula": "1799001122001",
        "nombre_comercial": "Consultorio CRM",
        "categoria": "Doctores",
        "especialidad": "Psicólogo",
        "latitud": -0.16,
        "longitud": -78.45,
        "precio_consulta": 30.00,
        "membresia_fija": 10.00
    }
    res_doc = client.post("/api/admin/proveedores", json=doctor_payload, headers={"Authorization": f"Bearer {admin_token}"})
    doc_id = res_doc.json()["id"]
    
    pac_data = {
        "email": "paciente_crm@test.com",
        "password": "pacientepassword",
        "nombres": "Sofía",
        "apellidos": "Mendoza",
        "cedula": "1755555555",
        "celular_whatsapp": "+593985555555",
        "origen_informacion": "TikTok"
    }
    res_pac = client.post("/api/auth/register-paciente", json=pac_data)
    pac_token = res_pac.json()["access_token"]
    
    # 2. Paciente hace click en contactar
    client.post(f"/api/proveedores/{doc_id}/contactar", headers={"Authorization": f"Bearer {pac_token}"})
    
    # 3. Login de doctor y ver prospecto (lead inicial: CONTACTADO)
    login_doc = client.post("/api/auth/login", data={"username": "doctor_crm@medicya.com", "password": "doctorpassword"})
    doc_token = login_doc.json()["access_token"]
    
    metrics = client.get("/api/proveedores/dashboard/metricas", headers={"Authorization": f"Bearer {doc_token}"}).json()
    assert metrics["lista_prospectos"][0]["estado_lead"] == "CONTACTADO"
    lead_id = metrics["lista_prospectos"][0]["id"]
    
    # 4. Cambiar estado a AGENDADO
    res_crm_update = client.put(
        f"/api/proveedores/leads/{lead_id}/estado",
        json={"estado_lead": "AGENDADO"},
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    assert res_crm_update.status_code == 200
    
    # Verificar cambio
    metrics_post = client.get("/api/proveedores/dashboard/metricas", headers={"Authorization": f"Bearer {doc_token}"}).json()
    assert metrics_post["lista_prospectos"][0]["estado_lead"] == "AGENDADO"

def test_payphone_payment_simulation():
    # 1. Crear doctor y generar factura
    db = TestingSessionLocal()
    user_prov = models.UsuarioSistema(
        email="doctor_pay@medicya.com",
        password_hash=deps.get_password_hash("doctorpassword"),
        rol=models.RolUsuario.PROVEEDOR,
        estado=models.EstadoUsuario.ACTIVO
    )
    db.add(user_prov)
    db.flush()
    prov = models.ProveedorServicio(
        usuario_id=user_prov.id,
        ruc_cedula="1711122233001",
        nombre_comercial="Centro Médico PayPhone",
        categoria=models.CategoriaProveedor.DOCTORES,
        latitud=-0.15,
        longitud=-78.44,
        precio_consulta=50.00,
        membresia_fija=10.00,
        es_premium=True # Membresía $15
    )
    db.add(prov)
    db.flush()
    db.commit()
    
    # Ejecutar mensual de facturación
    billing_cron.run_monthly_billing(db)
    
    factura = db.query(models.Factura).filter(models.Factura.proveedor_id == prov.id).first()
    assert factura is not None
    assert float(factura.monto_total) == 15.00 # $15 premium fija
    
    # 2. Login de doctor y pagar factura vía PayPhone
    login_doc = client.post("/api/auth/login", data={"username": "doctor_pay@medicya.com", "password": "doctorpassword"})
    doc_token = login_doc.json()["access_token"]
    
    checkout_payload = {
        "metodo": "PayPhone",
        "telefono_payphone": "0987654321"
    }
    
    res_pay = client.post(
        f"/api/billing/facturas/{factura.id}/pagar",
        json=checkout_payload,
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    assert res_pay.status_code == 200
    assert "TX-PAYPHONE-" in res_pay.json()["transaction_id"]
    assert res_pay.json()["estado_cuenta_proveedor"] == "ACTIVO"
    
    # 3. Comprobar factura pagada
    db.refresh(factura)
    assert factura.estado == models.EstadoFactura.PAGADA
    db.close()


def test_advertising_management_and_ai_agent():
    db = TestingSessionLocal()
    
    # 1. Crear Administrador en base de datos
    admin_user = models.UsuarioSistema(
        email="admin_ads@medicya.com",
        password_hash=deps.get_password_hash("adminpassword"),
        rol=models.RolUsuario.ADMIN,
        estado=models.EstadoUsuario.ACTIVO
    )
    db.add(admin_user)
    
    # 2. Crear Proveedor / Doctor
    prov_user = models.UsuarioSistema(
        email="doctor_ads@medicya.com",
        password_hash=deps.get_password_hash("doctorpassword"),
        rol=models.RolUsuario.PROVEEDOR,
        estado=models.EstadoUsuario.ACTIVO
    )
    db.add(prov_user)
    db.flush()
    
    prov = models.ProveedorServicio(
        usuario_id=prov_user.id,
        ruc_cedula="1798765432001",
        nombre_comercial="Clinica Dental Ads",
        categoria=models.CategoriaProveedor.DOCTORES,
        especialidad="Odontología",
        latitud=-0.22,
        longitud=-78.50,
        precio_consulta=30.00,
        membresia_fija=10.00
    )
    db.add(prov)
    
    # 3. Crear Paciente
    pac_user = models.UsuarioSistema(
        email="patient_ads@medicya.com",
        password_hash=deps.get_password_hash("patientpassword"),
        rol=models.RolUsuario.PACIENTE,
        estado=models.EstadoUsuario.ACTIVO
    )
    db.add(pac_user)
    db.flush()
    
    paciente = models.Paciente(
        usuario_id=pac_user.id,
        nombres="Juan",
        apellidos="Anuncio",
        cedula="1711122233",
        celular_whatsapp="0999888777",
        origen_informacion=models.CanalAtribucion.TIKTOK
    )
    db.add(paciente)
    db.commit()

    # --- LOGINS ---
    # Login Admin
    res_login_admin = client.post("/api/auth/login", data={"username": "admin_ads@medicya.com", "password": "adminpassword"})
    admin_token = res_login_admin.json()["access_token"]
    
    # Login Doctor
    res_login_doc = client.post("/api/auth/login", data={"username": "doctor_ads@medicya.com", "password": "doctorpassword"})
    doc_token = res_login_doc.json()["access_token"]
    
    # Login Paciente
    res_login_pac = client.post("/api/auth/login", data={"username": "patient_ads@medicya.com", "password": "patientpassword"})
    pac_token = res_login_pac.json()["access_token"]

    # --- PROCESO ---
    # 1. Admin lista usuarios globales
    res_users = client.get("/api/admin/usuarios", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_users.status_code == 200
    user_emails = [u["email"] for u in res_users.json()]
    assert "admin_ads@medicya.com" in user_emails
    assert "doctor_ads@medicya.com" in user_emails
    assert "patient_ads@medicya.com" in user_emails

    # 2. Doctor solicita campaña de publicidad ($10 USD)
    ad_payload = {
        "plataformas": "Instagram, TikTok",
        "cantidad_vistas": 500,
        "precio": 10.00
    }
    res_ad = client.post(
        "/api/proveedores/solicitar-publicidad",
        json=ad_payload,
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    assert res_ad.status_code == 201
    
    # Comprobar que se le asignó/creó una factura pendiente con el monto de la publicidad
    factura = db.query(models.Factura).filter(models.Factura.proveedor_id == prov.id).first()
    assert factura is not None
    assert float(factura.monto_publicidad) == 10.00
    assert float(factura.monto_total) == 10.00

    # 3. Paciente solicita campaña de publicidad de su negocio ($20 USD)
    res_ad_pac = client.post(
        "/api/pacientes/solicitar-publicidad",
        json={
            "plataformas": "Facebook",
            "cantidad_vistas": 1000,
            "precio": 20.00
        },
        headers={"Authorization": f"Bearer {pac_token}"}
    )
    assert res_ad_pac.status_code == 200
    assert "registrada con éxito" in res_ad_pac.json()["message"]

    # 4. Admin lista campañas publicitarias
    res_camps = client.get("/api/admin/publicidad/campanas", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_camps.status_code == 200
    campanas = res_camps.json()
    assert len(campanas) >= 2
    
    doctor_camp = [c for c in campanas if c["email"] == "doctor_ads@medicya.com"][0]
    assert doctor_camp["plataformas"] == "Instagram, TikTok"
    assert doctor_camp["precio"] == 10.00
    assert doctor_camp["estado"] == "PENDIENTE"

    # 5. Admin ejecuta Agente de Publicidad IA
    res_agent = client.post("/api/admin/publicidad/ejecutar-agente", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_agent.status_code == 200
    logs = res_agent.json()["logs"]
    assert any("[Agente IA]" in log for log in logs)

    # Verificar que el estado de las campañas progresó a "EN_CURSO" o "COMPLETADA"
    db.expire_all()
    camps_after = db.query(models.SolicitudPublicidad).all()
    for c in camps_after:
        if c.usuario_id in [prov_user.id, pac_user.id]:
            assert c.estado in ["EN_CURSO", "COMPLETADA"]
            assert c.veces_publicado > 0

    # 6. Admin suspende un usuario genérico
    res_status = client.post(
        f"/api/admin/usuarios/{pac_user.id}/estado?nuevo_estado=BLOQUEADO",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_status.status_code == 200
    db.refresh(pac_user)
    assert pac_user.estado == models.EstadoUsuario.BLOQUEADO
    db.close()


def test_premium_social_networks():
    # 1. Crear un médico básico (no Premium)
    db = TestingSessionLocal()
    basic_hash = deps.get_password_hash("password123")
    basic_user = models.UsuarioSistema(
        email="medico_basico@medicya.com",
        password_hash=basic_hash,
        rol=models.RolUsuario.PROVEEDOR,
        estado=models.EstadoUsuario.ACTIVO
    )
    db.add(basic_user)
    db.flush()
    basic_prov = models.ProveedorServicio(
        usuario_id=basic_user.id,
        ruc_cedula="1234567890",
        nombre_comercial="Dr. Básico",
        categoria=models.CategoriaProveedor.DOCTORES,
        especialidad="General",
        latitud=-0.18,
        longitud=-78.46,
        precio_consulta=Decimal("20.00"),
        es_premium=False
    )
    db.add(basic_prov)
    
    # 2. Crear un médico Premium
    premium_hash = deps.get_password_hash("password123")
    premium_user = models.UsuarioSistema(
        email="medico_prem@medicya.com",
        password_hash=premium_hash,
        rol=models.RolUsuario.PROVEEDOR,
        estado=models.EstadoUsuario.ACTIVO
    )
    db.add(premium_user)
    db.flush()
    premium_prov = models.ProveedorServicio(
        usuario_id=premium_user.id,
        ruc_cedula="1234567891",
        nombre_comercial="Dr. Premium",
        categoria=models.CategoriaProveedor.DOCTORES,
        especialidad="Pediatría",
        latitud=-0.185,
        longitud=-78.465,
        precio_consulta=Decimal("35.00"),
        es_premium=True
    )
    db.add(premium_prov)
    db.commit()
    
    # 3. Loguear a ambos
    res_login_basic = client.post("/api/auth/login", data={"username": "medico_basico@medicya.com", "password": "password123"})
    assert res_login_basic.status_code == 200
    basic_token = res_login_basic.json()["access_token"]
    
    res_login_prem = client.post("/api/auth/login", data={"username": "medico_prem@medicya.com", "password": "password123"})
    assert res_login_prem.status_code == 200
    prem_token = res_login_prem.json()["access_token"]

    # 4. Intentar actualizar redes del médico básico (debe fallar con 403)
    res_upd_basic = client.put(
        "/api/proveedores/me/redes",
        json={"link_instagram": "https://instagram.com/basic", "link_tiktok": "https://tiktok.com/@basic"},
        headers={"Authorization": f"Bearer {basic_token}"}
    )
    assert res_upd_basic.status_code == 403
    assert "Premium" in res_upd_basic.json()["detail"]

    # 5. Actualizar redes del médico Premium (debe tener éxito)
    res_upd_prem = client.put(
        "/api/proveedores/me/redes",
        json={
            "link_instagram": "https://instagram.com/premium",
            "link_tiktok": "https://tiktok.com/@premium",
            "link_facebook": "https://facebook.com/premium"
        },
        headers={"Authorization": f"Bearer {prem_token}"}
    )
    assert res_upd_prem.status_code == 200
    assert "actualizadas exitosamente" in res_upd_prem.json()["message"]

    # 6. Consultar mapa público y verificar visibilidad condicionada
    res_map = client.get("/api/proveedores/mapa")
    assert res_map.status_code == 200
    map_providers = res_map.json()
    
    basic_in_map = [p for p in map_providers if p["id"] == basic_prov.id][0]
    prem_in_map = [p for p in map_providers if p["id"] == premium_prov.id][0]
    
    # El básico no debe tener links
    assert basic_in_map["link_instagram"] is None
    assert basic_in_map["link_tiktok"] is None
    assert basic_in_map["link_facebook"] is None
    
    # El premium debe mostrar los links configurados
    assert prem_in_map["link_instagram"] == "https://instagram.com/premium"
    assert prem_in_map["link_tiktok"] == "https://tiktok.com/@premium"
    assert prem_in_map["link_facebook"] == "https://facebook.com/premium"
    
    db.close()

def test_admin_marketing_masivo_con_adjuntos():
    # 1. Login de Administrador
    login_data = {
        "username": "admin@medicya.com",
        "password": "admin123"
    }
    response = client.post("/api/auth/login", data=login_data)
    admin_token = response.json()["access_token"]
    
    # 2. Registrar paciente
    pac_data = {
        "email": "marketing_paciente@test.com",
        "password": "pacientepassword",
        "nombres": "Pedro",
        "apellidos": "Sánchez",
        "cedula": "1755443322",
        "celular_whatsapp": "+593981234567",
        "origen_informacion": "TikTok"
    }
    res_pac = client.post("/api/auth/register-paciente", json=pac_data)
    assert res_pac.status_code == 200
    
    # 3. Enviar Correo Masivo con video y adjunto
    email_payload = {
        "asunto": "Campaña de Verano",
        "cuerpo": "Nuevas promociones de salud",
        "link_video": "https://youtube.com/watch?v=campana",
        "archivo_adjunto_url": "https://drive.com/folder/documento.pdf"
    }
    res_email = client.post(
        "/api/admin/correos-masivos",
        json=email_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_email.status_code == 200
    assert "Correo masivo enviado" in res_email.json()["message"]
    
    # 4. Enviar WhatsApp Masivo con video y adjunto
    wa_payload = {
        "mensaje": "Hola! Te compartimos nuestra campaña del mes.",
        "link_video": "https://youtube.com/watch?v=whatsapp",
        "archivo_adjunto_url": "https://images.com/banner.png"
    }
    res_wa = client.post(
        "/api/admin/whatsapp-masivo",
        json=wa_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_wa.status_code == 200
    assert "WhatsApp" in res_wa.json()["message"]
    assert len(res_wa.json()["logs"]) > 0

