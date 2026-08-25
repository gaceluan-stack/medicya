import logging
import httpx
from app.config import settings

logger = logging.getLogger("whatsapp_service")

async def send_whatsapp_notification(
    provider_phone: str,
    patient_name: str,
    patient_lastname: str,
    patient_cedula: str
) -> bool:
    """
    Envía una notificación de WhatsApp al profesional indicando que un cliente
    ha solicitado contacto con su información personal (Nombre, Apellido, Cédula).
    """
    message = (
        f"📢 *Medic YA - Nuevo Prospecto*\n\n"
        f"Hola, un paciente está interesado en tus servicios:\n"
        f"👤 *Nombre:* {patient_name} {patient_lastname}\n"
        f"🆔 *Documento:* {patient_cedula}\n\n"
        f"Por favor, revisa tu panel de Medic YA para más detalles."
    )
    
    # Payload para la API de WhatsApp (Simulado o Twilio / Meta Cloud API)
    payload = {
        "messaging_product": "whatsapp",
        "to": provider_phone,
        "type": "text",
        "text": {
            "body": message
        }
    }
    
    logger.info(f"Enviando WhatsApp a {provider_phone}: {message}")
    
    # Imprimir en consola de desarrollo para depuración rápida
    try:
        print(f"\n--- [WHATSAPP OUTGOING] TO: {provider_phone} ---\n{message}\n---------------------------------------\n")
    except UnicodeEncodeError:
        clean_message = message.encode('ascii', errors='replace').decode('ascii')
        print(f"\n--- [WHATSAPP OUTGOING] TO: {provider_phone} ---\n{clean_message}\n---------------------------------------\n")
    
    # Intento de petición HTTP (silenciado si es mock)
    if "mock" in settings.WHATSAPP_API_URL:
        return True
        
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}
            response = await client.post(
                settings.WHATSAPP_API_URL,
                json=payload,
                headers=headers,
                timeout=5.0
            )
            return response.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Error al enviar notificación de WhatsApp: {str(e)}")
        return False

async def send_custom_whatsapp(to_phone: str, message: str) -> bool:
    """
    Envía un mensaje de WhatsApp personalizado (texto libre) a un destinatario.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {
            "body": message
        }
    }
    
    logger.info(f"Enviando WhatsApp personalizado a {to_phone}: {message}")
    
    try:
        print(f"\n--- [WHATSAPP OUTGOING CUSTOM] TO: {to_phone} ---\n{message}\n---------------------------------------\n")
    except UnicodeEncodeError:
        clean_message = message.encode('ascii', errors='replace').decode('ascii')
        print(f"\n--- [WHATSAPP OUTGOING CUSTOM] TO: {to_phone} ---\n{clean_message}\n---------------------------------------\n")
        
    if "mock" in settings.WHATSAPP_API_URL:
        return True
        
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}
            response = await client.post(
                settings.WHATSAPP_API_URL,
                json=payload,
                headers=headers,
                timeout=5.0
            )
            return response.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Error al enviar WhatsApp personalizado: {str(e)}")
        return False
