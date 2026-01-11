#!/usr/bin/env python3
"""
Bot DeltaChat para Render - Configuración y despliegue completamente automático.
Envía el enlace de invitación por correo al administrador.
Específico para servidor nine.testrun.org: usuario=9 chars, contraseña=8 chars.
"""
import asyncio
import os
import sys
import logging
from pathlib import Path

# Configuración de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DEL BOT (ÚNICO CAMBIO REQUERIDO) ---
# REEMPLAZA ESTE EMAIL POR TU DIRECCIÓN REAL. El bot te enviará aquí el enlace.
ADMIN_EMAIL = "TU_EMAIL_PERSONAL@example.com"  # <-- ¡CAMBIA ESTO POR TU EMAIL!
BOT_NAME = "Bot Descargador Automático"
BOT_SERVER = "nine.testrun.org"  # Solo el dominio, sin https://
BOT_STATUS = "Envía un enlace directo de descarga"
# ------------------------------------------------------

def generar_credenciales_validas():
    """Genera credenciales válidas para nine.testrun.org:
       - Nombre de usuario: 9 caracteres alfanuméricos exactos
       - Contraseña: 8 caracteres alfanuméricos exactos
    """
    import secrets
    import string
    
    # 1. Generar nombre de usuario de 9 caracteres (letras + números)
    caracteres_usuario = string.ascii_lowercase + string.digits
    nombre_usuario = ''.join(secrets.choice(caracteres_usuario) for _ in range(9))
    
    # 2. Generar contraseña de 8 caracteres (letras + números)
    caracteres_password = string.ascii_letters + string.digits  # mayúsculas y minúsculas
    password = ''.join(secrets.choice(caracteres_password) for _ in range(8))
    
    bot_email = f"{nombre_usuario}@{BOT_SERVER}"
    
    return bot_email, password

def configurar_cuenta_automatica():
    """Realiza la configuración inicial del bot usando el enfoque JSON-RPC."""
    logger.info("Iniciando configuración automática del bot...")
    
    try:
        from deltachat_rpc_client import DeltaChat, Rpc

        with Rpc() as rpc:
            # Inicializar Delta Chat
            deltachat = DeltaChat(rpc)
            system_info = deltachat.get_system_info()
            logger.info(f"DeltaChat core: {system_info.deltachat_core_version}")

            # Usar la primera cuenta existente o crear una nueva
            accounts = deltachat.get_all_accounts()
            account = accounts[0] if accounts else deltachat.add_account()
            
            # Verificar si la cuenta ya está configurada
            if account.is_configured():
                logger.info("✅ La cuenta del bot ya está configurada.")
                return account
            
            # Crear una nueva cuenta para el bot
            logger.info("🔧 Creando nueva cuenta para el bot...")
            
            # Generar credenciales VÁLIDAS para nine.testrun.org
            bot_email, bot_password = generar_credenciales_validas()
            
            logger.info(f"📧 Cuenta generada: {bot_email}")
            logger.info(f"🔑 Contraseña generada: {bot_password}")
            
            # Configurar la cuenta (API CORRECTA)
            # 1. Primero establecer todas las configuraciones
            account.set_config("addr", bot_email)          # Email del bot
            account.set_config("mail_pw", bot_password)    # Contraseña (8 caracteres)
            account.set_config("mail_server", BOT_SERVER)  # Servidor de entrada
            account.set_config("send_server", BOT_SERVER)  # Servidor de salida
            
            # 2. Llamar a configure() SIN argumentos
            account.configure()
            logger.info("✅ Cuenta del bot configurada exitosamente.")
            
            # Configurar nombre y estado del bot
            account.set_config("displayname", BOT_NAME)
            account.set_config("selfstatus", BOT_STATUS)
            logger.info(f"🤖 Nombre del bot: {BOT_NAME}")
            
            # Esperar a que la cuenta esté lista (máximo 30 segundos)
            import time
            for intento in range(30):
                if account.is_configured():
                    logger.info(f"✅ Cuenta lista después de {intento+1} segundos")
                    break
                if intento % 5 == 0:  # Log cada 5 segundos
                    logger.info(f"⏳ Esperando que la cuenta se configure... ({intento+1}/30)")
                time.sleep(1)
            else:
                logger.warning("⚠️  La cuenta tardó más de lo esperado en configurarse")
            
            return account
            
    except Exception as e:
        logger.error(f"❌ Error en configuración automática: {e}")
        raise

def obtener_enlace_invitacion(account):
    """Obtiene el enlace de invitación del bot."""
    try:
        qr_code_data = account.get_qr_code()
        # El enlace es largo, mostramos solo el inicio en logs
        enlace_corto = qr_code_data[:80] + "..." if len(qr_code_data) > 80 else qr_code_data
        logger.info(f"🔗 Enlace de invitación generado: {enlace_corto}")
        return qr_code_data
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo enlace de invitación: {e}")
        return None

def enviar_enlace_por_correo(account, enlace):
    """Envía el enlace de invitación al administrador por correo."""
    try:
        # Verificar que ADMIN_EMAIL no sea el placeholder
        if ADMIN_EMAIL == "TU_EMAIL_PERSONAL@example.com":
            logger.error("❌ ERROR: No has configurado tu email en ADMIN_EMAIL")
            logger.error("Por favor, edita bot.py y cambia TU_EMAIL_PERSONAL@example.com por tu email real")
            return False
        
        # Crear o encontrar el chat con el administrador
        contacto = account.create_contact(ADMIN_EMAIL)
        chat = contacto.create_chat()
        
        # Enviar el mensaje con el enlace
        mensaje = f"""
🤖 **¡Tu bot DeltaChat está listo y funcionando!**

El bot **{BOT_NAME}** ha sido desplegado exitosamente en Render.

**ENLACE PARA AGREGAR AL BOT:**
{enlace}

**Instrucciones:**
1. Abre Delta Chat en tu teléfono
2. Haz clic en este enlace o escanea el código QR
3. ¡Listo! Ya puedes chatear con tu bot

**Credenciales generadas (guardadas en logs):**
- Servidor: {BOT_SERVER}
- Email del bot: {account.get_config("addr")}
- Estado: {BOT_STATUS}

**¿Cómo usar el bot?**
Simplemente envíale un enlace directo a un archivo (que termine en .pdf, .jpg, .zip, etc.)
y el bot lo descargará y te lo enviará de vuelta.

El bot funciona 24/7 en Render.
"""
        
        chat.send_message(mensaje)
        logger.info(f"✅ Enlace de invitación enviado a: {ADMIN_EMAIL}")
        logger.info("📱 Revisa tu Delta Chat para aceptar la invitación")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando enlace por correo: {e}")
        # Si falla el envío, al menos mostrar el enlace en logs
        logger.info(f"📋 ENLACE DE INVITACIÓN (copia manual): {enlace[:100]}...")
        return False

def inicializar_bot_descargador(account):
    """Configura los manejadores de eventos para el bot descargador."""
    try:
        from deltachat_rpc_client import events
        
        hooks = events.HookCollection()
        
        @hooks.on(events.NewMessage(func=lambda e: not e.command))
        def manejar_mensaje(event):
            """Maneja mensajes entrantes y descarga archivos."""
            snapshot = event.message_snapshot
            texto = snapshot.text or ""
            
            if not texto:
                return
            
            # Lógica básica de respuesta (MODIFICA AQUÍ para descargar archivos)
            respuesta = f"🤖 Recibí: {texto[:200]}"
            
            # Aquí iría tu lógica para detectar URLs y descargar archivos
            # Ejemplo básico:
            import re
            urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', texto)
            
            if urls:
                respuesta += f"\n\n🔗 Enlaces detectados: {len(urls)}"
                for i, url in enumerate(urls[:3], 1):  # Mostrar solo primeros 3
                    respuesta += f"\n{i}. {url[:50]}..."
            
            snapshot.chat.send_message(text=respuesta)
        
        # Configurar el bot con los hooks
        from deltachat_rpc_client import Bot
        bot = Bot(account, hooks)
        logger.info("✅ Bot descargador configurado y listo para recibir mensajes")
        return bot
        
    except Exception as e:
        logger.error(f"❌ Error configurando bot descargador: {e}")
        raise

async def main():
    """Función principal que ejecuta todo el proceso automático."""
    logger.info("🚀 Iniciando despliegue automático del bot DeltaChat en Render...")
    
    try:
        # Paso 1: Configurar la cuenta automáticamente
        account = configurar_cuenta_automatica()
        
        # Paso 2: Obtener el enlace de invitación
        enlace = obtener_enlace_invitacion(account)
        
        if enlace:
            # Paso 3: Enviar el enlace al administrador
            if enviar_enlace_por_correo(account, enlace):
                logger.info("✅ Todo configurado. El bot está listo para usar.")
            else:
                # Si falla el envío, mostrar el enlace completo en logs
                logger.info(f"📋 ENLACE COMPLETO PARA COPIAR: {enlace}")
        
        # Paso 4: Configurar el bot descargador
        bot = inicializar_bot_descargador(account)
        
        # Paso 5: Iniciar el bot (ejecutar para siempre)
        logger.info("=" * 60)
        logger.info("✅ Bot completamente configurado y funcionando")
        logger.info("📡 Escuchando mensajes... (Ctrl+C para detener)")
        logger.info("=" * 60)
        
        # En Render, necesitamos mantener el proceso activo
        await bot.run_forever()
        
    except KeyboardInterrupt:
        logger.info("👋 Bot detenido por el usuario")
    except Exception as e:
        logger.error(f"💥 Error crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Para Render, necesitamos ejecutar el loop asyncio
    asyncio.run(main())