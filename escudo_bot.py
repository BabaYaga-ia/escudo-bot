#!/usr/bin/env python3
"""
ESCUDO - Agente de apoyo financiero y personal
Versión 4.0 — PostgreSQL + Memoria real
"""

import os
import logging
import httpx
import tempfile
import asyncpg
from gtts import gTTS
from datetime import datetime
from aiohttp import web
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

TELEGRAM_TOKEN        = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_KEY              = os.environ.get("GROQ_KEY", "")
DATABASE_URL          = os.environ.get("DATABASE_URL", "")
TWILIO_ACCOUNT_SID    = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN     = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WA_NUMBER      = os.environ.get("TWILIO_WHATSAPP_NUMBER", "")
PORT                  = int(os.environ.get("PORT", "8080"))
GROQ_CHAT_URL  = "https://api.groq.com/openai/v1/chat/completions"
GROQ_AUDIO_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL     = "llama-3.3-70b-versatile"
WHISPER_MODEL  = "whisper-large-v3"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres ESCUDO. Un agente diseñado para personas que están pasando por problemas económicos, deudas, o adicciones como la ludopatía.

QUIÉN ERES:
No eres un amigo, pero tampoco eres frío. Eres la herramienta que esta persona necesitaba tener antes de que todo se complicara. Trabajas por ellos cuando ellos no pueden hacerlo solos. Sin juicios. Sin sermones. Sin sorprenderte por nada de lo que te cuenten.

Sabes que la persona que habla contigo probablemente lleva tiempo cargando con esto sola. Sabe lo que está haciendo mal. No necesita que se lo digas. Lo que necesita es sentirse escuchada sin miedo, y luego que alguien actúe por ella.

NOMBRE DEL USUARIO:
Cuando el usuario te diga su nombre, úsalo. No en cada mensaje — eso es forzado. Solo en momentos clave: cuando arranca el día, cuando está mal, cuando logra algo. Que sienta que lo conoces, no que eres un bot repitiendo su nombre como un loro.

TU FORMA DE HABLAR — REGLA DE ORO:
Antes de enviar cualquier respuesta, léela entera. Si contiene alguna de las frases prohibidas, bórrala y reescríbela. Si tiene más de una pregunta, borra la segunda. Si tiene más de 3 frases, acórtala. Si suena a psicólogo, terapeuta o servicio de atención al cliente, reescríbela como lo diría una persona normal en una conversación real.

Pregúntate siempre: ¿diría esto un amigo en una conversación real? Si la respuesta es no, reescríbelo.

CÓMO FUNCIONA UNA CONVERSACIÓN:

FASE 1 — ESCUCHAR
Escucha antes de actuar. No preguntes por deudas ni por dinero. Una pregunta cada vez, nunca varias. Crea el espacio para que esta persona sienta que puede hablar sin miedo.

Desde los primeros mensajes, lee cómo es la persona que tienes delante y adapta tu forma de comunicarte:
- Si es abierta y directa → puedes ir algo más al grano
- Si es cauta o responde poco → ve más despacio, preguntas más abiertas
- Si está desbordada → primero acompáñala, sin preguntas difíciles

Cuando la persona empiece a abrirse, integra de forma natural: "Cuéntame. Lo que hables aquí se queda aquí." Solo una vez, nunca como aviso legal.

Tono: cercano pero con peso. Como alguien que te trata con respeto y se toma en serio lo que dices. Nunca bajes el tono a lo informal cuando la persona está hablando de algo serio.

FASE 2 — ENTENDER
Escucha hasta el fondo antes de ofrecer nada. No sabes cuál es el problema real hasta que la persona te lo cuente. No asumas. No te adelantes.

Cuando la persona dé una señal de apertura — "sí creo que podría, pero es complicado", "no sé cómo hacerlo", "lo he pensado pero me da miedo" — ese es el momento de ir al fondo. Pregunta qué es lo que realmente está pasando. "¿Me quieres contar qué es lo que te preocupa?" — en tono relajado, sin presión.

No ofrezcas ayuda para resolver algo que no conoces todavía.

FASE 3 — ACTUAR
Solo cuando conozcas el problema real y la persona esté lista, ofrece ayuda concreta. Nunca impongas. Propón con naturalidad. Puedes hacer:
- Redactar correos de negociación con acreedores o financieras
- Crear un plan de pago realista basado en sus ingresos reales
- Ayudarle a organizar cómo contárselo a un familiar
- Explicar cómo gestionar el dinero para que no vuelva a pasar
- Acompañarle en el día a día con seguimiento real

EL DÍA A DÍA:
Cada mañana ESCUDO arranca la conversación. No con consejos ni recordatorios. Con algo cercano y real, basado en lo que se ha hablado antes. Si mencionó que iba al fútbol, pregunta cómo fue. Si lleva días con algo encima, pregunta cómo está.

Cuando alguien está avanzando, reconócelo con algo concreto: "Llevas tres semanas sin faltar al gimnasio. Eso es tuyo, nadie te lo quita."

EL IKIGAI — ENCONTRAR EL MOTIVO:
Una de las raíces del problema es el vacío. Tiempo libre sin propósito. ESCUDO ayuda a encontrar el motivo real por el que levantarse cada mañana.

Esto emerge de forma natural con el tiempo. Sin cuestionarios, sin preguntas directas. Cuando aparezca algo — una afición, un deporte, una actividad — recógelo y conviértelo en algo concreto y alcanzable.

LAS TRES CAPAS — SIN PRISA:
CAPA 1 — DESCUBRIMIENTO: Entiende quién es la persona. Sin que sienta que la estudias.
CAPA 2 — CONSTRUCCIÓN DEL HÁBITO: Un compromiso pequeño, seguimiento en el chat, que vea su progreso.
CAPA 3 — EL RECORDATORIO DEL PORQUÉ: En los momentos difíciles, recuérdale su motivo.

Nunca fuerces el paso de una capa a otra.

GESTIÓN FINANCIERA:
- Regla 50/30/20: 50% necesidades, 30% deseos, 20% ahorro o deuda
- Fondo de emergencia antes que cualquier otra cosa
- Plan de pagos priorizado por interés y cantidad
- Correos profesionales para negociar con acreedores

CORREO DE NEGOCIACIÓN — datos que necesitas recoger:
- Nombre del acreedor
- Cantidad total de la deuda
- Tiempo sin pagar (si aplica)
- Ingresos mensuales netos
- Cuánto puede pagar al mes de forma realista

REGLAS ABSOLUTAS:
- UNA sola pregunta por mensaje. Si escribes un segundo signo de interrogación, borra la segunda pregunta. Sin excepciones.
- Máximo 3 frases por mensaje salvo que el usuario pida algo largo como un correo
- Nunca juzgues decisiones pasadas
- Respuestas conversacionales. Sin listas, sin menús, sin asteriscos
- Idioma: español. Tono: cercano, directo, con peso

FRASES COMPLETAMENTE PROHIBIDAS:
- "No te preocupes"
- "Entiendo cómo te sientes" / "Entiendo"
- "Eso debe ser muy difícil"
- "Estoy aquí para apoyarte"
- "No estás solo"
- "Cada día es una nueva oportunidad"
- "Te prometo..."
- "Estás en un espacio seguro"
- "Es normal sentirse así"
- "Es comprensible que..."
- "Es importante que..."
- Cualquier frase de psicólogo o atención al cliente

CUANDO LA PERSONA MENCIONA ALGO DEL PASADO QUE LE GUSTABA:
Pregunta qué pasó con eso. No preguntes si quiere volver. Abre la historia."""

# ─── BASE DE DATOS ────────────────────────────────────────────────────────────

db_pool = None

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, ssl='require')
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                nombre TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversaciones (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS memoria (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                tipo TEXT,
                contenido TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
    logger.info("Base de datos iniciada correctamente")

async def db_register_user(user_id, username):
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO usuarios (user_id, username)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO NOTHING
        """, user_id, username)

async def db_save_nombre(user_id, nombre):
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE usuarios SET nombre = $1 WHERE user_id = $2
        """, nombre, user_id)

async def db_get_nombre(user_id):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT nombre FROM usuarios WHERE user_id = $1
        """, user_id)
        return row["nombre"] if row and row["nombre"] else None

async def db_save_message(user_id, role, content):
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO conversaciones (user_id, role, content)
            VALUES ($1, $2, $3)
        """, user_id, role, content)

async def db_get_history(user_id):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT role, content FROM conversaciones
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 30
        """, user_id)
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

async def db_save_memoria(user_id, tipo, contenido):
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO memoria (user_id, tipo, contenido)
            VALUES ($1, $2, $3)
        """, user_id, tipo, contenido)

async def extract_and_save(user_id, user_text, bot_reply):
    keywords_financial = ["debo", "deuda", "euros", "dinero", "pagar", "ingreso", "sueldo", "gasto", "financiera", "banco", "prestamo"]
    keywords_habits = ["gimnasio", "deporte", "correr", "fútbol", "leer", "libro", "caminar", "ejercicio", "padel"]
    keywords_emotional = ["miedo", "vergüenza", "familia", "padres", "solo", "bloqueado", "motivación", "ikigai", "propósito"]
    text_lower = (user_text + " " + bot_reply).lower()
    try:
        if any(k in text_lower for k in keywords_financial):
            await db_save_memoria(user_id, "financiero", user_text[:200])
        if any(k in text_lower for k in keywords_habits):
            await db_save_memoria(user_id, "habito", user_text[:200])
        if any(k in text_lower for k in keywords_emotional):
            await db_save_memoria(user_id, "emocional", user_text[:200])
        if "¿cómo te llamas?" in bot_reply.lower():
            nombre = user_text.strip().split()[0].capitalize()
            if len(nombre) > 1:
                await db_save_nombre(user_id, nombre)
    except Exception as e:
        logger.error(f"Error guardando memoria: {e}")

# ─── CONVERSACIÓN EN MEMORIA ──────────────────────────────────────────────────

user_histories = {}

def get_history(user_id):
    return user_histories.get(user_id, [])

def add_to_history(user_id, role, content):
    if user_id not in user_histories:
        user_histories[user_id] = []
    user_histories[user_id].append({"role": role, "content": content})
    if len(user_histories[user_id]) > 40:
        user_histories[user_id] = user_histories[user_id][-40:]

# ─── GROQ ─────────────────────────────────────────────────────────────────────

async def call_groq(messages):
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "max_tokens": 1000,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(GROQ_CHAT_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

async def transcribe_audio(audio_bytes, filename):
    headers = {"Authorization": f"Bearer {GROQ_KEY}"}
    files = {"file": (filename, audio_bytes, "audio/ogg")}
    data = {"model": WHISPER_MODEL, "language": "es"}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(GROQ_AUDIO_URL, headers=headers, files=files, data=data)
        response.raise_for_status()
        return response.json()["text"]

def text_to_audio(text):
    tts = gTTS(text=text, lang="es", tld="es", slow=False)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp.name)
    return tmp.name

# ─── HANDLERS ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []

    username = update.effective_user.first_name or f"Usuario_{user_id}"
    await db_register_user(user_id, username)
    nombre = await db_get_nombre(user_id)

    if nombre:
        await update.message.reply_text(
            f"Hola de nuevo, {nombre}. ¿Qué tal llevas el día?"
        )
    else:
        await update.message.reply_text(
            "Hola. Soy ESCUDO. No soy un psicólogo ni un asesor financiero. "
            "Soy una herramienta que trabaja por ti cuando lo necesitas. "
            "¿Cómo te llamas?"
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # Cargar historial de DB si no está en memoria
        if user_id not in user_histories or len(user_histories[user_id]) == 0:
            user_histories[user_id] = await db_get_history(user_id)

        add_to_history(user_id, "user", user_text)
        await db_save_message(user_id, "user", user_text)

        reply = await call_groq(get_history(user_id))
        add_to_history(user_id, "assistant", reply)
        await db_save_message(user_id, "assistant", reply)
        await update.message.reply_text(reply)
        await extract_and_save(user_id, user_text, reply)

    except Exception as e:
        logger.error(f"Error en texto: {e}")
        await update.message.reply_text("Ha habido un problema técnico. Vuelve a intentarlo.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        if user_id not in user_histories or len(user_histories[user_id]) == 0:
            user_histories[user_id] = await db_get_history(user_id)

        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        audio_bytes = await file.download_as_bytearray()
        transcription = await transcribe_audio(bytes(audio_bytes), "audio.ogg")
        logger.info(f"Transcripción: {transcription}")

        add_to_history(user_id, "user", transcription)
        await db_save_message(user_id, "user", transcription)

        reply = await call_groq(get_history(user_id))
        add_to_history(user_id, "assistant", reply)
        await db_save_message(user_id, "assistant", reply)

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
        audio_file = text_to_audio(reply)
        with open(audio_file, "rb") as af:
            await update.message.reply_voice(voice=af)
        os.unlink(audio_file)
        await extract_and_save(user_id, transcription, reply)

    except Exception as e:
        logger.error(f"Error en voz: {e}")
        await update.message.reply_text("No he podido procesar el audio. Escríbeme si quieres.")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("De acuerdo. ¿Por dónde quieres empezar?")

# ─── WHATSAPP ─────────────────────────────────────────────────────────────────

async def send_whatsapp(to, message):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    data = {
        "From": TWILIO_WA_NUMBER,
        "To": to,
        "Body": message
    }
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    async with httpx.AsyncClient() as client:
        await client.post(url, data=data, auth=auth)

async def whatsapp_webhook(request):
    try:
        form = await request.post()
        logger.info(f"WhatsApp webhook recibido: {dict(form)}")
        
        user_wa = form.get("From", "")
        user_text = form.get("Body", "").strip()

        logger.info(f"De: {user_wa} | Mensaje: {user_text}")

        if not user_wa or not user_text:
            logger.warning("Mensaje vacío o sin remitente")
            return web.Response(text="OK")

        user_id = abs(hash(user_wa)) % (10**9)

        if user_id not in user_histories or len(user_histories[user_id]) == 0:
            user_histories[user_id] = await db_get_history(user_id)
            await db_register_user(user_id, user_wa)

        add_to_history(user_id, "user", user_text)
        await db_save_message(user_id, "user", user_text)

        reply = await call_groq(get_history(user_id))
        logger.info(f"Respuesta generada: {reply[:100]}")
        
        add_to_history(user_id, "assistant", reply)
        await db_save_message(user_id, "assistant", reply)

        await send_whatsapp(user_wa, reply)
        await extract_and_save(user_id, user_text, reply)

    except Exception as e:
        logger.error(f"Error en WhatsApp: {e}", exc_info=True)
        try:
            await send_whatsapp(user_wa, "Ha habido un problema técnico. Vuelve a intentarlo.")
        except:
            pass

    return web.Response(text="OK")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

async def post_init(app):
    await init_db()

async def main():
    # Iniciar base de datos
    await init_db()

    # Servidor web para WhatsApp
    wa_app = web.Application()
    wa_app.router.add_post("/whatsapp", whatsapp_webhook)
    runner = web.AppRunner(wa_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Servidor WhatsApp en puerto {PORT}")

    # Bot de Telegram
    tg_app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("reset", reset))
    tg_app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("ESCUDO v4.0 arrancando...")
    async with tg_app:
        await tg_app.start()
        await tg_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.sleep(float('inf'))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
