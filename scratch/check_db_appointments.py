from app.db.database import SessionLocal
from app.db import models

db = SessionLocal()
try:
    print("Listing all registered appointments for doctors:")
    appointments = db.query(models.CitaProveedor).all()
    for appt in appointments:
        print(f"ID: {appt.id}, Provider: {appt.proveedor.nombre_comercial}, Patient: {appt.paciente_nombre}, Date: {appt.fecha}, Time: {appt.hora_inicio}-{appt.hora_fin}, Status: {appt.estado}")
        
    print("\nListing all doctors:")
    doctors = db.query(models.ProveedorServicio).all()
    for d in doctors:
        print(f"ID: {d.id}, Name: {d.nombre_comercial}, Premium: {d.es_premium}")
        
except Exception as e:
    print("Error:", e)
finally:
    db.close()
