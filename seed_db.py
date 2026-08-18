# seed_db.py - Seed database for Medic YA
from app.db.database import SessionLocal, engine, Base
from app.db import models
from app.api import deps
from decimal import Decimal

# Asegurar creación de tablas
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Verificar si está vacío
if db.query(models.ProveedorServicio).count() == 0:
    providers_data = [
        {
            "email": "carlos.andrade@medicya.com",
            "password": "password123",
            "ruc_cedula": "1711223344001",
            "nombre_comercial": "Dr. Carlos Andrade - Cardiología",
            "categoria": models.CategoriaProveedor.DOCTORES,
            "especialidad": "Cardiólogo Pediatra",
            "latitud": -0.180653,
            "longitud": -78.467834,
            "precio_consulta": Decimal("45.00"),
            "es_premium": True,
        },
        {
            "email": "maria.vaca@medicya.com",
            "password": "password123",
            "ruc_cedula": "1711223355001",
            "nombre_comercial": "Dra. María Vaca - Pediatría",
            "categoria": models.CategoriaProveedor.DOCTORES,
            "especialidad": "Pediatra",
            "latitud": -0.200000,
            "longitud": -78.430000,
            "precio_consulta": Decimal("35.00"),
            "es_premium": False,
        },
        {
            "email": "bella.spa@medicya.com",
            "password": "password123",
            "ruc_cedula": "1722334455001",
            "nombre_comercial": "Bella Estética & Spa",
            "categoria": models.CategoriaProveedor.SPAS,
            "especialidad": "Tratamientos Faciales y Corporales",
            "latitud": -0.178000,
            "longitud": -78.465000,
            "precio_consulta": Decimal("25.00"),
            "es_premium": True,
        },
        {
            "email": "aqua.spa@medicya.com",
            "password": "password123",
            "ruc_cedula": "1722334466001",
            "nombre_comercial": "Aqua Spa & Bienestar",
            "categoria": models.CategoriaProveedor.SPAS,
            "especialidad": "Masajes Terapéuticos",
            "latitud": -0.185000,
            "longitud": -78.472000,
            "precio_consulta": Decimal("20.00"),
            "es_premium": False,
        },
        {
            "email": "clinica.metropolitana@medicya.com",
            "password": "password123",
            "ruc_cedula": "1799887766001",
            "nombre_comercial": "Clínica Metropolitana Quito",
            "categoria": models.CategoriaProveedor.CLINICAS,
            "especialidad": "Urgencias y Especialidades",
            "latitud": -0.175000,
            "longitud": -78.462000,
            "precio_consulta": Decimal("80.00"),
            "es_premium": False,
        }
    ]

    for p in providers_data:
        password_hash = deps.get_password_hash(p["password"])
        user = models.UsuarioSistema(
            email=p["email"],
            password_hash=password_hash,
            rol=models.RolUsuario.PROVEEDOR,
            estado=models.EstadoUsuario.ACTIVO
        )
        db.add(user)
        db.flush()

        from app.services.sector_classifier import classify_location
        ciudad_auto, sector_auto = classify_location(p["latitud"], p["longitud"])

        prov = models.ProveedorServicio(
            usuario_id=user.id,
            ruc_cedula=p["ruc_cedula"],
            nombre_comercial=p["nombre_comercial"],
            categoria=p["categoria"],
            especialidad=p["especialidad"],
            latitud=p["latitud"],
            longitud=p["longitud"],
            precio_consulta=p["precio_consulta"],
            membresia_fija=Decimal("40.00") if p["es_premium"] else Decimal("25.00"),
            es_premium=p["es_premium"],
            ciudad=ciudad_auto,
            sector=sector_auto
        )
        db.add(prov)
        print(f"Sembrado exitoso: {p['nombre_comercial']}")

    db.commit()
    print("Base de datos sembrada correctamente.")
else:
    print("La base de datos ya contiene registros de proveedores.")

db.close()
