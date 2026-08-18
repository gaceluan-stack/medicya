import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Medic YA API"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-medic-ya-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 días para sesión del paciente
    
    # Base de Datos: Target PostgreSQL. Fallback a SQLite para pruebas locales fáciles.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./medic_ya.db")
    
    # Mock WhatsApp Settings
    WHATSAPP_API_URL: str = os.getenv("WHATSAPP_API_URL", "https://api.whatsapp.com/mock")
    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "mock-token-whatsapp")
    
    # SMTP Email Settings
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "info@medicya.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "mock-smtp-password")
    
    # Google Maps API Key
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    
    class Config:
        case_sensitive = True

settings = Settings()
