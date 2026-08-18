# seed_gye.py - Seed database for Medic YA in Guayaquil
from app.db.database import SessionLocal
from app.db import models
from app.api import deps
from decimal import Decimal

db = SessionLocal()

# Verificar si ya existe el primer RUC de GYE
existing = db.query(models.ProveedorServicio).filter(models.ProveedorServicio.ruc_cedula == "0911223344001").first()

if not existing:
    providers_data = [
        {
            "email": "roberto.noboa@medicya.com",
            "password": "password123",
            "ruc_cedula": "0911223344001",
            "nombre_comercial": "Dr. Roberto Noboa - Pediatría GYE",
            "categoria": models.CategoriaProveedor.DOCTORES,
            "especialidad": "Pediatra Neonatólogo",
            "latitud": -2.1894,
            "longitud": -79.8890,
            "precio_consulta": Decimal("50.00"),
            "es_premium": True,
        },
        {
            "email": "aura.spa@medicya.com",
            "password": "password123",
            "ruc_cedula": "0911223355001",
            "nombre_comercial": "Aura Spa Guayaquil",
            "categoria": models.CategoriaProveedor.SPAS,
            "especialidad": "Masajes y Limpieza Facial",
            "latitud": -2.1950,
            "longitud": -79.8950,
            "precio_consulta": Decimal("30.00"),
            "es_premium": False,
        },
        {
            "email": "diana.chang@medicya.com",
            "password": "password123",
            "ruc_cedula": "0911223366001",
            "nombre_comercial": "Dra. Diana Chang - Ginecología GYE",
            "categoria": models.CategoriaProveedor.DOCTORES,
            "especialidad": "Ginecóloga Obstetra",
            "latitud": -2.1850,
            "longitud": -79.8820,
            "precio_consulta": Decimal("40.00"),
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
        print(f"Sembrado GYE exitoso: {p['nombre_comercial']}")

    db.commit()
    print("Base de datos (Guayaquil) sembrada correctamente.")
else:
    print("Los proveedores de Guayaquil ya existen en la base de datos.")

db.close()
