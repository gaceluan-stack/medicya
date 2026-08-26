import sys
import math
import asyncio
from datetime import datetime, timedelta, date
from decimal import Decimal
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, get_db
from app.db import models
from app.services.email import send_email_notification
from app.services.whatsapp import send_whatsapp_notification

def run_monthly_billing(db: Session):
    """
    Cierre mensual de facturación (Día 1):
    1. Para cada proveedor, cuenta los clics de los últimos 30 días.
    2. Calcula el monto por clics ($5 por cada 1000 clics).
    3. Genera una factura con vencimiento a 10 días.
    4. Cambia el estado del proveedor a PENDIENTE_PAGO.
    5. Envía una notificación de emisión (Día 1).
    """
    print(f"[{datetime.utcnow()}] Iniciando cierre de facturación mensual...")
    proveedores = db.query(models.ProveedorServicio).all()
    
    fecha_limite_clics = datetime.utcnow() - timedelta(days=30)
    fecha_vencimiento = datetime.utcnow().date() + timedelta(days=10)
    
    facturas_creadas = 0
    for prov in proveedores:
        # Contar citas del proveedor en los últimos 30 días
        citas_count = db.query(models.CitaProveedor).filter(
            models.CitaProveedor.proveedor_id == prov.id,
            models.CitaProveedor.created_at >= fecha_limite_clics
        ).count()
        
        # Calcular cargo variable según el volumen de citas agendadas por WhatsApp:
        # - Primeras citas agendadas hasta cumplir 20: $25 USD
        # - De 21 a 40 citas: $50 USD
        # - De 41 o más citas: $75 USD
        monto_variable = Decimal("0.00")
        if citas_count > 0:
            if citas_count <= 20:
                monto_variable = Decimal("25.00")
            elif citas_count <= 40:
                monto_variable = Decimal("50.00")
            else:
                monto_variable = Decimal("75.00")
        
        # Suscripción mensual base única de $5.00 USD para todos los proveedores
        monto_fijo = Decimal("5.00")
        monto_total = monto_fijo + monto_variable
        
        # Crear factura
        nueva_factura = models.Factura(
            proveedor_id=prov.id,
            fecha_emision=datetime.utcnow().date(),
            fecha_vencimiento=fecha_vencimiento,
            monto_fijo=monto_fijo,
            monto_clics=monto_variable, # Reutilizamos la columna monto_clics para almacenar la tarifa por citas sin requerir migraciones
            monto_total=monto_total,
            estado=models.EstadoFactura.PENDIENTE
        )
        db.add(nueva_factura)
        
        # Actualizar el estado del usuario del proveedor a PENDIENTE_PAGO
        usuario = prov.usuario
        usuario.estado = models.EstadoUsuario.PENDIENTE_PAGO
        db.add(usuario)
        
        # Enviar WhatsApp Informativo (Día 1)
        try:
            asyncio.run(send_whatsapp_notification(
                provider_phone=prov.ruc_cedula, # Usamos ruc_cedula como teléfono dummy para la prueba
                patient_name="Medic YA",
                patient_lastname="Facturación",
                patient_cedula=f"Factura mensual emitida por ${monto_total:.2f} USD. Vence el {fecha_vencimiento}."
            ))
        except Exception as e:
            print(f"Error al enviar WhatsApp en día 1: {e}")
            
        # Enviar correo de notificación (Día 1)
        cuerpo_correo = (
            f"<h2>Factura de Servicios - Medic YA</h2>"
            f"<p>Estimado/a <strong>{prov.nombre_comercial}</strong>,</p>"
            f"<p>Se ha generado tu factura mensual para el periodo actual:</p>"
            f"<ul>"
            f"  <li><strong>Suscripción Fija Mensual:</strong> ${monto_fijo:.2f} USD</li>"
            f"  <li><strong>Citas Agendadas (Últimos 30 días):</strong> {citas_count} citas (${monto_variable:.2f} USD de tarifa variable)</li>"
            f"  <li><strong>Monto Total a Pagar:</strong> ${monto_total:.2f} USD</li>"
            f"  <li><strong>Fecha de Vencimiento:</strong> {fecha_vencimiento} (Plazo de 10 días para pago)</li>"
            f"</ul>"
            f"<p>Evita la suspensión de tu perfil realizando el pago desde tu panel.</p>"
        )
        send_email_notification(
            to_email=usuario.email,
            subject="Medic YA - Factura Mensual Generada",
            body=cuerpo_correo
        )
        facturas_creadas += 1
        
    db.commit()
    print(f"[{datetime.utcnow()}] Cierre mensual completado. {facturas_creadas} facturas generadas.")

def run_daily_overdue_check(db: Session):
    """
    Control diario de facturas y recordatorios:
    - Día 7: Envía recordatorio amistoso si la factura sigue PENDIENTE (7 días desde emisión).
    - Día 10: Bloquea preventivamente al proveedor si la factura sigue PENDIENTE (10 o más días desde emisión).
    """
    print(f"[{datetime.utcnow()}] Iniciando revisión diaria de facturas y mora...")
    hoy = datetime.utcnow().date()
    
    facturas_pendientes = db.query(models.Factura).filter(
        models.Factura.estado != models.EstadoFactura.PAGADA
    ).all()
    
    proveedores_bloqueados = 0
    for fac in facturas_pendientes:
        prov = db.query(models.ProveedorServicio).filter(
            models.ProveedorServicio.id == fac.proveedor_id
        ).first()
        
        if not prov:
            continue
            
        usuario = prov.usuario
        dias_desde_emision = (hoy - fac.fecha_emision).days
        
        # Día 7: Recordatorio amable (Faltan 3 días para vencimiento)
        if dias_desde_emision == 7:
            # Enviar WhatsApp
            try:
                asyncio.run(send_whatsapp_notification(
                    provider_phone=prov.ruc_cedula,
                    patient_name="Medic YA",
                    patient_lastname="Recordatorio",
                    patient_cedula=f"Recordatorio de factura pendiente por ${fac.monto_total:.2f} USD. Faltan 3 días para el vencimiento."
                ))
            except Exception as e:
                print(f"Error al enviar WhatsApp en día 7: {e}")
                
            # Enviar Correo
            cuerpo_correo = (
                f"<h2>Recordatorio de Pago - Medic YA</h2>"
                f"<p>Estimado/a <strong>{prov.nombre_comercial}</strong>,</p>"
                f"<p>Te recordamos amablemente que tu factura mensual está próxima a vencer:</p>"
                f"<ul>"
                f"  <li><strong>Monto:</strong> ${fac.monto_total:.2f} USD</li>"
                f"  <li><strong>Vencimiento:</strong> {fac.fecha_vencimiento} (Faltan 3 días)</li>"
                f"</ul>"
                f"<p>Por favor, realiza el pago desde tu panel para mantener tu perfil activo en el directorio.</p>"
            )
            send_email_notification(
                to_email=usuario.email,
                subject="Medic YA - Recordatorio de Vencimiento de Factura",
                body=cuerpo_correo
            )
            print(f"Recordatorio de Día 7 enviado a {prov.nombre_comercial}")
            
        # Día 10: Notificación de suspensión preventiva de cuenta
        elif dias_desde_emision >= 10 or fac.fecha_vencimiento < hoy:
            fac.estado = models.EstadoFactura.VENCIDA
            db.add(fac)
            
            if usuario.estado != models.EstadoUsuario.BLOQUEADO:
                usuario.estado = models.EstadoUsuario.BLOQUEADO
                db.add(usuario)
                proveedores_bloqueados += 1
                
                # Enviar WhatsApp Alerta Suspensión
                try:
                    asyncio.run(send_whatsapp_notification(
                        provider_phone=prov.ruc_cedula,
                        patient_name="Medic YA",
                        patient_lastname="Suspensión",
                        patient_cedula=f"Alerta: Perfil suspendido temporalmente por mora en factura de ${fac.monto_total:.2f} USD."
                    ))
                except Exception as e:
                    print(f"Error al enviar WhatsApp en día 10: {e}")
                
                # Enviar Correo Suspensión
                cuerpo_suspendido = (
                    f"<h2>Aviso de Suspensión de Perfil - Medic YA</h2>"
                    f"<p>Estimado/a <strong>{prov.nombre_comercial}</strong>,</p>"
                    f"<p>Lamentamos informarte que tu perfil en la plataforma pública de Medic YA "
                    f"ha sido <strong>suspendido / bloqueado</strong> debido a una factura pendiente "
                    f"de pago por más de 10 días.</p>"
                    f"<ul>"
                    f"  <li><strong>Factura ID:</strong> {fac.id}</li>"
                    f"  <li><strong>Monto Vencido:</strong> ${fac.monto_total:.2f} USD</li>"
                    f"  <li><strong>Fecha de Vencimiento:</strong> {fac.fecha_vencimiento}</li>"
                    f"</ul>"
                    f"<p>Realiza tu pago desde tu panel de facturación para reactivar tu perfil al instante.</p>"
                )
                send_email_notification(
                    to_email=usuario.email,
                    subject="Medic YA - ALERTA: Cuenta Suspendida por Falta de Pago",
                    body=cuerpo_suspendido
                )
                print(f"Suspensión de Día 10 aplicada a {prov.nombre_comercial}")
                
    db.commit()
    print(f"[{datetime.utcnow()}] Revisión diaria de mora completada. {proveedores_bloqueados} proveedores bloqueados.")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        if len(sys.argv) > 1:
            command = sys.argv[1]
            if command == "monthly":
                run_monthly_billing(db)
            elif command == "daily":
                run_daily_overdue_check(db)
            else:
                print("Comando desconocido. Use 'monthly' o 'daily'")
        else:
            print("Ejecutando revisión de mora diaria...")
            run_daily_overdue_check(db)
    finally:
        db.close()
