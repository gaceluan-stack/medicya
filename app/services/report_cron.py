import sys
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db import models
from app.services.whatsapp import send_custom_whatsapp

async def send_all_doctors_daily_reports(db: Session = None):
    """
    Envía un reporte diario por WhatsApp a todos los doctores Premium
    con su agenda para el día siguiente.
    """
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True
        
    try:
        # Huso horario de Ecuador (UTC-5)
        tz_ecuador = timezone(timedelta(hours=-5))
        now_ecuador = datetime.now(tz_ecuador)
        tomorrow_date = (now_ecuador + timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow_display = (now_ecuador + timedelta(days=1)).strftime("%d/%m/%Y")
        
        print(f"[{now_ecuador}] Ejecutando reporte diario de citas para la fecha: {tomorrow_date}")
        
        # Buscar todos los proveedores Premium que tengan celular_whatsapp
        proveedores = db.query(models.ProveedorServicio).filter(
            models.ProveedorServicio.es_premium == True,
            models.ProveedorServicio.celular_whatsapp != None,
            models.ProveedorServicio.celular_whatsapp != ""
        ).all()
        
        for prov in proveedores:
            # Buscar citas para mañana ordenadas por hora de inicio
            citas = db.query(models.CitaProveedor).filter(
                models.CitaProveedor.proveedor_id == prov.id,
                models.CitaProveedor.fecha == tomorrow_date
            ).order_by(models.CitaProveedor.hora_inicio).all()
            
            # Formatear el reporte de WhatsApp
            message = f"📅 *Medic YA - Tu Agenda de Mañana* 📅\n\n"
            message += f"Hola Dr/a. *{prov.nombre_comercial}*,\n"
            message += f"Este es el reporte de tu agenda para mañana *{tomorrow_display}*:\n\n"
            
            if not citas:
                message += "✨ *No tienes citas ni bloqueos programados para mañana.* ¡Disfruta tu día!\n"
            else:
                message += "📋 *Detalle de tu Agenda:*\n"
                for index, cita in enumerate(citas, 1):
                    tipo = "Cita" if cita.estado == "RESERVADA" else "Bloqueo"
                    emoji = "👤" if cita.estado == "RESERVADA" else "🔒"
                    paciente = cita.paciente_nombre
                    celular = cita.paciente_celular
                    celular_str = f" ({celular})" if celular else ""
                    
                    message += f"{index}. {emoji} *{cita.hora_inicio} a {cita.hora_fin}:* {tipo} - {paciente}{celular_str}\n"
                
                total_citas = sum(1 for c in citas if c.estado == "RESERVADA")
                total_bloqueos = sum(1 for c in citas if c.estado == "BLOQUEADA")
                
                message += f"\n📊 *Resumen:* {total_citas} citas reservadas, {total_bloqueos} espacios bloqueados.\n"
            
            message += f"\nRevisa tu panel de Medic YA para reprogramar o gestionar tus citas."
            
            # Enviar notificación
            try:
                await send_custom_whatsapp(prov.celular_whatsapp, message)
            except Exception as e:
                print(f"Error al enviar WhatsApp a {prov.nombre_comercial} ({prov.celular_whatsapp}): {e}")
                
    finally:
        if should_close_db:
            db.close()

def get_seconds_until_5am_ecuador() -> float:
    # Ecuador es UTC-5
    tz_ecuador = timezone(timedelta(hours=-5))
    now = datetime.now(tz_ecuador)
    
    # 5:00 AM de hoy
    target = now.replace(hour=5, minute=0, second=0, microsecond=0)
    
    # Si ya pasó las 5:00 AM hoy, el target es las 5:00 AM de mañana
    if now >= target:
        target += timedelta(days=1)
        
    delta = target - now
    return delta.total_seconds()

async def start_daily_report_scheduler():
    print("[Report Scheduler] Iniciando programador diario de reportes a las 5 AM...")
    while True:
        seconds_to_wait = get_seconds_until_5am_ecuador()
        hrs = int(seconds_to_wait // 3600)
        mins = int((seconds_to_wait % 3600) // 60)
        print(f"[Report Scheduler] Durmiendo por {hrs}h {mins}m ({seconds_to_wait} seg) hasta las 5:00 AM Ecuador...")
        
        await asyncio.sleep(seconds_to_wait)
        
        # Una vez despertado, ejecutar el reporte
        try:
            await send_all_doctors_daily_reports()
        except Exception as e:
            print(f"[Report Scheduler] Error al enviar reportes diarios: {e}")
            
        # Dormir 2 minutos adicionales para evitar ejecuciones repetidas instantáneas
        await asyncio.sleep(120)

if __name__ == "__main__":
    db = SessionLocal()
    try:
        print("Ejecutando envío manual de reporte diario a doctores Premium...")
        asyncio.run(send_all_doctors_daily_reports(db))
    finally:
        db.close()
