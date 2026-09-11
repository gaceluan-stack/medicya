import logging
import httpx
from app.config import settings

logger = logging.getLogger("whatsapp_service")

def build_whatsapp_payload(url: str, to_phone: str, message: str, token: str) -> dict:
    clean_phone = to_phone.replace("+", "").replace(" ", "").replace("-", "")
    url_lower = url.lower()
    
    if "ultramsg.com" in url_lower:
        return {
            "token": token,
            "to": clean_phone,
            "body": message
        }
        
    if "evolution" in url_lower or "wassenger" in url_lower or "green-api" in url_lower:
        return {
            "number": clean_phone,
            "phone": clean_phone,
            "to": clean_phone,
            "message": message,
            "text": message
        }
        
    if "graph.facebook.com" in url_lower or "facebook.com" in url_lower:
        return {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "text",
            "text": {"body": message}
        }
        
    return {
        "to": clean_phone,
        "phone": clean_phone,
        "message": message,
        "body": message,
        "text": message,
        "token": token
    }

async def send_whatsapp_notification(
    provider_phone: str,
    patient_name: str,
    patient_lastname: str,
    patient_cedula: str
) -> bool:
    message = (
        f"📢 *Medic YA - Nuevo Prospecto*\n\n"
        f"Hola, un paciente está interesado en tus servicios:\n"
        f"👤 *Nombre:* {patient_name} {patient_lastname}\n"
        f"🆔 *Documento:* {patient_cedula}\n\n"
        f"Por favor, revisa tu panel de Medic YA para más detalles."
    )
    
    return await send_custom_whatsapp(provider_phone, message)

async def send_custom_whatsapp(to_phone: str, message: str, session_token: str = None) -> bool:
    """
    Envía un mensaje de WhatsApp personalizado a un número de teléfono.
    Si el médico tiene un session_token activo (QR vinculado), el mensaje
    se transmite a través de la sesión propia del médico.
    """
    clean_phone = to_phone.replace("+", "").replace(" ", "").replace("-", "")
    payload = build_whatsapp_payload(settings.WHATSAPP_API_URL, clean_phone, message, settings.WHATSAPP_TOKEN)
    if session_token:
        payload["session_token"] = session_token
    
    logger.info(f"Enviando WhatsApp a {clean_phone} (Sesión Médico: {session_token or 'PLATAFORMA'}): {message}")
    
    try:
        sender_info = f" [SESION MEDICO: {session_token}]" if session_token else " [SESION CENTRAL]"
        print(f"\n--- [WHATSAPP OUTGOING{sender_info}] TO: {clean_phone} ---\n{message}\n---------------------------------------\n")
    except UnicodeEncodeError:
        clean_message = message.encode('ascii', errors='replace').decode('ascii')
        print(f"\n--- [WHATSAPP OUTGOING] TO: {clean_phone} ---\n{clean_message}\n---------------------------------------\n")
        
    if "mock" in settings.WHATSAPP_API_URL.lower():
        print(f"ℹ️ [WHATSAPP MOCK MODE] Mensaje registrado en logs del servidor. Sesión activa: {session_token or 'CENTRAL'}.")
        return True
        
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            }
            response = await client.post(
                settings.WHATSAPP_API_URL,
                json=payload,
                headers=headers,
                timeout=8.0
            )
            logger.info(f"Respuesta de WhatsApp API ({response.status_code}): {response.text}")
            return response.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Error al enviar mensaje por WhatsApp API: {str(e)}")
        return False
