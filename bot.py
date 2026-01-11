#!/usr/bin/env python3
"""
Bot DeltaChat para Render - Descarga archivos de enlaces directos.
Configuración automática al primer inicio.
"""

from deltabot_cli import BotCli
from deltachat2 import MsgData, events
import os
import re
import requests
import tempfile
import logging

# Configurar logging para ver lo que pasa en Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar el CLI del bot
bot_name = "descargador-render"
cli = BotCli(bot_name)

# ==================== CONFIGURACIÓN AUTOMÁTICA ====================

def configuracion_automatica():
    """
    Configura el bot automáticamente al primer inicio.
    Esto reemplaza los comandos manuales: init, config, link
    """
    # Ruta donde se guarda la configuración del bot
    config_dir = os.path.join(os.path.expanduser("~"), ".config", bot_name)
    flag_file = os.path.join(config_dir, "CONFIGURADO.flag")
    
    # Si ya está configurado, no hacer nada
    if os.path.exists(flag_file):
        logger.info("✅ El bot ya estaba configurado previamente.")
        return
    
    logger.info("⚙️  Configurando el bot por primera vez...")
    
    try:
        # 1. Obtener cuenta desde variable de entorno (OBLIGATORIO)
        bot_account = os.getenv("BOT_ACCOUNT")
        
        if not bot_account:
            error_msg = "❌ ERROR: Variable BOT_ACCOUNT no configurada."
            error_msg += "\nPor favor, configura BOT_ACCOUNT en Render:"
            error_msg += "\nValor: DCACCOUNT:https://nine.testrun.org/new"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Usando cuenta: {bot_account}")
        
        # 2. Inicializar la cuenta (equivalente a: python bot.py init DCACCOUNT:...)
        logger.info("Inicializando cuenta DeltaChat...")
        cli.init(bot_account)
        
        # 3. Configurar nombre y estado (equivalente a: python bot.py config ...)
        logger.info("Configurando nombre y estado...")
        cli.config("displayname", "🤖 Bot Descargador")
        cli.config("selfstatus", "Envía un enlace directo y te devuelvo el archivo")
        
        # 4. Marcar como configurado
        os.makedirs(config_dir, exist_ok=True)
        with open(flag_file, 'w') as f:
            f.write("Configuración completada")
        
        logger.info("✅ Configuración automática completada.")
        
        # 5. Generar y mostrar enlace de invitación (IMPORTANTE: Copiar de logs)
        logger.info("=" * 60)
        logger.info("🪄 GENERANDO ENLACE DE INVITACIÓN (Copia esto de los logs):")
        # Llamamos internamente a la función que genera el enlace
        enlace = generar_enlace_invitacion()
        if enlace:
            logger.info(f"🔗 ENLACE: {enlace}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error en configuración automática: {e}")
        raise

def generar_enlace_invitacion():
    """Genera y devuelve el enlace de invitación del bot"""
    try:
        # Esta es una versión simplificada de lo que hace cli.link()
        # En producción, cli.link() funciona directamente
        cli.link()  # Esto imprimirá el enlace en los logs
        return "(Ver enlace en los logs de Render arriba)"
    except Exception as e:
        logger.error(f"Error generando enlace: {e}")
        return None

# Ejecutar configuración automática al importar
configuracion_automatica()

# ==================== LÓGICA DEL BOT DESCARGADOR ====================

@cli.on(events.NewMessage)
def manejar_mensaje(bot, accid, event):
    """Maneja mensajes entrantes, busca URLs y descarga archivos"""
    msg = event.msg
    texto = msg.text or ""
    chat_id = msg.chat_id
    
    # Ignorar mensajes del propio bot
    if msg.is_from_self:
        return
    
    logger.info(f"Mensaje recibido de {msg.sender.addr}: {texto[:100]}")
    
    # Buscar URLs en el mensaje
    urls = encontrar_urls(texto)
    
    if not urls:
        # Si no hay URL, enviar ayuda
        ayuda = (
            "🤖 **Bot Descargador de Archivos**\n\n"
            "Envía un enlace de descarga directa (que termine en .pdf, .zip, .jpg, etc.)\n"
            "y te devolveré el archivo.\n\n"
            "Ejemplo: https://ejemplo.com/documento.pdf"
        )
        bot.rpc.send_msg(accid, chat_id, MsgData(text=ayuda))
        return
    
    # Procesar la primera URL encontrada
    url = urls[0]
    
    try:
        # Notificar que se está procesando
        bot.rpc.send_msg(accid, chat_id, MsgData(
            text=f"⏳ Descargando archivo desde:\n{url[:100]}..."
        ))
        
        # Descargar el archivo
        archivo_descargado = descargar_archivo(url)
        
        if archivo_descargado:
            # Enviar el archivo de vuelta
            with open(archivo_descargado['ruta'], 'rb') as f:
                datos_archivo = MsgData(
                    file=f,
                    filename=archivo_descargado['nombre'],
                    text=f"✅ Archivo descargado: {archivo_descargado['nombre']}"
                )
                bot.rpc.send_msg(accid, chat_id, datos_archivo)
            
            # Limpiar archivo temporal
            os.unlink(archivo_descargado['ruta'])
            logger.info(f"Archivo {archivo_descargado['nombre']} enviado correctamente")
        else:
            bot.rpc.send_msg(accid, chat_id, MsgData(
                text="❌ No se pudo descargar el archivo. ¿Es un enlace directo?"
            ))
    
    except Exception as e:
        logger.error(f"Error procesando {url}: {e}")
        bot.rpc.send_msg(accid, chat_id, MsgData(
            text=f"❌ Error: {str(e)[:200]}"
        ))

def encontrar_urls(texto):
    """Encuentra URLs en el texto del mensaje"""
    # Patrón simple para URLs
    patron = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
    return re.findall(patron, texto)

def descargar_archivo(url, max_tamano_mb=50):
    """
    Descarga un archivo desde una URL.
    max_tamano_mb: Límite de tamaño en MB (por seguridad)
    """
    try:
        # Configurar headers para simular navegador
        headers = {
            'User-Agent': 'Mozilla/5.0 DeltaChat-Bot/1.0'
        }
        
        # Hacer solicitud HEAD primero para verificar
        respuesta_head = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        respuesta_head.raise_for_status()
        
        # Verificar tamaño (si la cabecera Content-Length está disponible)
        tamano_bytes = respuesta_head.headers.get('Content-Length')
        if tamano_bytes:
            tamano_mb = int(tamano_bytes) / (1024 * 1024)
            if tamano_mb > max_tamano_mb:
                raise ValueError(f"Archivo demasiado grande ({tamano_mb:.1f}MB > {max_tamano_mb}MB)")
        
        # Obtener nombre del archivo
        nombre_archivo = obtener_nombre_archivo(url, respuesta_head.headers)
        
        # Descargar el archivo
        respuesta = requests.get(url, headers=headers, stream=True, timeout=30)
        respuesta.raise_for_status()
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=nombre_archivo) as tmp:
            # Descargar en chunks para manejar archivos grandes
            tamano_descargado = 0
            for chunk in respuesta.iter_content(chunk_size=8192):
                if chunk:
                    tamano_descargado += len(chunk)
                    # Verificar tamaño durante la descarga
                    if tamano_descargado > max_tamano_mb * 1024 * 1024:
                        os.unlink(tmp.name)
                        raise ValueError(f"Archivo excede el límite de {max_tamano_mb}MB")
                    tmp.write(chunk)
            
            ruta_archivo = tmp.name
        
        logger.info(f"Archivo descargado: {nombre_archivo} ({tamano_descargado/1024:.1f}KB)")
        
        return {
            'ruta': ruta_archivo,
            'nombre': nombre_archivo,
            'tamano': tamano_descargado
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red: {e}")
        return None
    except Exception as e:
        logger.error(f"Error descargando archivo: {e}")
        return None

def obtener_nombre_archivo(url, headers):
    """Obtiene un nombre de archivo adecuado desde la URL o headers"""
    # Intentar desde Content-Disposition
    content_disp = headers.get('Content-Disposition', '')
    if 'filename=' in content_disp:
        # Extraer nombre del archivo de la cabecera
        import re
        match = re.search(r'filename="([^"]+)"', content_disp)
        if match:
            return match.group(1)
    
    # Extraer de la URL
    nombre = url.split('/')[-1].split('?')[0]
    
    # Si no tiene extensión, añadir una por defecto
    if '.' not in nombre:
        # Intentar deducir del Content-Type
        content_type = headers.get('Content-Type', '')
        if 'pdf' in content_type:
            nombre = f"{nombre}.pdf"
        elif 'zip' in content_type or 'compressed' in content_type:
            nombre = f"{nombre}.zip"
        elif 'image' in content_type:
            if 'jpeg' in content_type or 'jpg' in content_type:
                nombre = f"{nombre}.jpg"
            elif 'png' in content_type:
                nombre = f"{nombre}.png"
        else:
            nombre = f"{nombre}.bin"
    
    # Limpiar nombre (remover caracteres problemáticos)
    nombre = re.sub(r'[^\w\-_.]', '_', nombre)
    
    return nombre or "archivo_descargado"

# ==================== INICIO DEL BOT ====================

if __name__ == "__main__":
    logger.info("🚀 Iniciando Bot Descargador de Archivos...")
    cli.start()