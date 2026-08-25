import sys
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db import models
from app.services.whatsapp import send_custom_whatsapp
from app.services.email import send_email_notification

async def send_all_doctors_today_reports(db: Session = None):
    """
    Envía un resumen de las citas de hoy a las 7:00 PM por WhatsApp y Correo
    a todos los doctores Premium.
    """
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True
        
    try:
        # Huso horario de Ecuador (UTC-5)
        tz_ecuador = timezone(timedelta(hours=-5))
        now_ecuador = datetime.now(tz_ecuador)
        today_date = now_ecuador.strftime("%Y-%m-%d")
        today_display = now_ecuador.strftime("%d/%m/%Y")
        
        print(f"[{now_ecuador}] Ejecutando reporte de citas de hoy para la fecha: {today_date}")
        
        # Buscar proveedores Premium
        proveedores = db.query(models.ProveedorServicio).filter(
            models.ProveedorServicio.es_premium == True
        ).all()
        
        for prov in proveedores:
            # Buscar citas agendadas de hoy
            citas = db.query(models.CitaProveedor).filter(
                models.CitaProveedor.proveedor_id == prov.id,
                models.CitaProveedor.fecha == today_date,
                models.CitaProveedor.estado == "RESERVADA"
            ).order_by(models.CitaProveedor.hora_inicio).all()
            
            # --- Formatear Mensaje de WhatsApp ---
            wa_message = f"✅ *Medic YA - Resumen de Atenciones de Hoy* ✅\n\n"
            wa_message += f"Hola Dr/a. *{prov.nombre_comercial}*,\n"
            wa_message += f"Este es el resumen de los pacientes agendados que atendiste hoy *{today_display}*:\n\n"
            
            if not citas:
                wa_message += "✨ *No tuviste citas programadas para hoy en tu agenda.*"
            else:
                wa_message += "📋 *Pacientes Atendidos:*\n"
                for index, cita in enumerate(citas, 1):
                    paciente = cita.paciente_nombre
                    celular = cita.paciente_celular
                    celular_str = f" ({celular})" if celular else ""
                    wa_message += f"{index}. 👤 *{cita.hora_inicio} a {cita.hora_fin}:* {paciente}{celular_str}\n"
                
                wa_message += f"\n📊 *Total:* {len(citas)} pacientes programados hoy."
                
            wa_message += f"\n\n¡Gracias por tu gran labor hoy con tus pacientes!"
            
            # --- Formatear Mensaje de Correo ---
            email_subject = f"Medic YA - Resumen de Atenciones Hoy ({today_display})"
            email_body = f"<h2>Resumen de Atenciones de Hoy - Medic YA</h2>"
            email_body += f"<p>Estimado/a Dr/a. <strong>{prov.nombre_comercial}</strong>,</p>"
            email_body += f"<p>Este es el resumen de los pacientes programados en tu agenda hoy <strong>{today_display}</strong>:</p>"
            
            if not citas:
                email_body += "<p><em>No tuviste citas programadas para hoy en tu agenda.</em></p>"
            else:
                email_body += "<ul>"
                for cita in citas:
                    paciente = cita.paciente_nombre
                    celular = cita.paciente_celular
                    celular_str = f" ({celular})" if celular else ""
                    email_body += f"  <li><strong>{cita.hora_inicio} a {cita.hora_fin}:</strong> {paciente}{celular_str}</li>"
                email_body += "</ul>"
                email_body += f"<p><strong>Total de pacientes hoy:</strong> {len(citas)}</p>"
                
            email_body += f"<br><p>¡Gracias por tu gran labor y compromiso con tus pacientes hoy!</p>"
            email_body += f"<p>Atentamente,<br><strong>El Equipo de Medic YA</strong></p>"
            
            # Enviar WhatsApp si hay número
            if prov.celular_whatsapp:
                try:
                    await send_custom_whatsapp(prov.celular_whatsapp, wa_message)
                except Exception as e:
                    print(f"Error al enviar WhatsApp hoy a {prov.nombre_comercial}: {e}")
                    
            # Enviar Correo si hay usuario e email
            if prov.usuario and prov.usuario.email:
                try:
                    send_email_notification(prov.usuario.email, email_subject, email_body)
                except Exception as e:
                    print(f"Error al enviar correo hoy a {prov.nombre_comercial}: {e}")
                    
    finally:
        if should_close_db:
            db.close()

async def send_all_doctors_tomorrow_reports(db: Session = None):
    """
    Envía un reporte diario por WhatsApp a todos los doctores Premium
    con su agenda para el día siguiente a las 8:00 PM.
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
        
        # Buscar proveedores Premium
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
            
            try:
                await send_custom_whatsapp(prov.celular_whatsapp, message)
            except Exception as e:
                print(f"Error al enviar WhatsApp mañana a {prov.nombre_comercial}: {e}")
                
    finally:
        if should_close_db:
            db.close()

async def start_daily_report_scheduler():
    print("[Report Scheduler] Iniciando programador diario de reportes (7:00 PM y 8:00 PM Ecuador)...")
    last_sent_today_report = None
    last_sent_tomorrow_report = None
    
    while True:
        tz_ecuador = timezone(timedelta(hours=-5))
        now_ecuador = datetime.now(tz_ecuador)
        today_str = now_ecuador.strftime("%Y-%m-%d")
        
        # 1. Reporte de hoy a las 7:00 PM (19:00)
        if now_ecuador.hour == 19 and now_ecuador.minute == 0:
            if last_sent_today_report != today_str:
                try:
                    await send_all_doctors_today_reports()
                    last_sent_today_report = today_str
                except Exception as e:
                    print(f"[Report Scheduler] Error al enviar reportes de hoy: {e}")
                    
        # 2. Reporte de mañana a las 8:00 PM (20:00)
        if now_ecuador.hour == 20 and now_ecuador.minute == 0:
            if last_sent_tomorrow_report != today_str:
                try:
                    await send_all_doctors_tomorrow_reports()
                    last_sent_tomorrow_report = today_str
                except Exception as e:
                    print(f"[Report Scheduler] Error al enviar reportes de mañana: {e}")
                    
        # Dormir 30 segundos antes de volver a verificar
        await asyncio.sleep(30)

if __name__ == "__main__":
    db = SessionLocal()
    try:
        if len(sys.argv) > 1:
            cmd = sys.argv[1]
            if cmd == "today":
                print("Ejecutando envío manual de reporte de HOY a doctores Premium...")
                asyncio.run(send_all_doctors_today_reports(db))
            elif cmd == "tomorrow":
                print("Ejecutando envío manual de reporte de MAÑANA a doctores Premium...")
                asyncio.run(send_all_doctors_tomorrow_reports(db))
            else:
                print("Comando desconocido. Use 'today' o 'tomorrow'")
        else:
            print("Ejecutando envío manual de ambos reportes...")
            asyncio.run(send_all_doctors_today_reports(db))
            asyncio.run(send_all_doctors_tomorrow_reports(db))
    finally:
        db.close()
