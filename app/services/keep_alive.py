import asyncio
import httpx
import logging

logger = logging.getLogger("keep_alive")

async def start_keep_alive():
    logger.info("[Keep Alive] Iniciando bucle de auto-ping para evitar suspensión en Render...")
    # Esperar 2 minutos para permitir un inicio limpio de la aplicación
    await asyncio.sleep(120)
    
    url = "https://medic-ya.onrender.com/"
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                # Realizar GET a la raíz del servidor para simular tráfico entrante
                response = await client.get(url, timeout=15.0)
                logger.info(f"[Keep Alive] Auto-ping exitoso en {url}. Status: {response.status_code}")
                print(f"[Keep Alive] Auto-ping exitoso en {url}. Status: {response.status_code}")
            except Exception as e:
                logger.error(f"[Keep Alive] Error en auto-ping: {str(e)}")
                print(f"[Keep Alive] Error en auto-ping: {str(e)}")
            
            # Dormir 10 minutos (600 segundos) para anticiparse a los 15 minutos de inactividad de Render
            await asyncio.sleep(600)
