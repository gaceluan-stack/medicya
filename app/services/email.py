import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

logger = logging.getLogger("email_service")

def send_email_notification(to_email: str, subject: str, body: str) -> bool:
    """
    Envía una notificación por correo electrónico.
    Si las credenciales son de prueba (mock) o falla la conexión,
    escribe un log detallado e imprime en pantalla para facilitar la depuración.
    """
    logger.info(f"Enviando Correo a {to_email} - Asunto: {subject}")
    
    # Imprimir en consola de desarrollo
    print(f"\n--- [EMAIL OUTGOING] TO: {to_email} ---\nSUBJECT: {subject}\nBODY:\n{body}\n-----------------------------------\n")
    
    # Si las credenciales SMTP son las por defecto, consideramos éxito en modo simulado
    if settings.SMTP_USERNAME == "info@medicya.com" or settings.SMTP_PASSWORD == "mock-smtp-password":
        return True

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_USERNAME
        msg["To"] = to_email
        msg["Subject"] = subject
        
        msg.attach(MIMEText(body, "html" if "<html" in body else "plain", "utf-8"))
        
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            if settings.SMTP_PORT == 587:
                server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USERNAME, to_email, msg.as_string())
        
        return True
    except Exception as e:
        logger.error(f"Fallo en el envío SMTP del correo a {to_email}: {str(e)}")
        return False
