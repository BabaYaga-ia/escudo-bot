#!/usr/bin/env python3
"""
ESCUDO - Bot de gestión financiera para Telegram
Versión 2.0 — Agente conversacional con voz
"""

import os
import logging
import httpx
import tempfile
from gtts import gTTS
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_KEY       = os.environ.get("GROQ_KEY", "")
GROQ_CHAT_URL  = "https://api.groq.com/openai/v1/chat/completions"
GROQ_AUDIO_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL     = "llama-3.3-70b-versatile"
WHISPER_MODEL  = "whisper-large-v3"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres ESCUDO, un agente de gestión financiera diseñado para personas con problemas económicos o adicciones como la ludopatía.

QUIÉN ERES:
No eres un amigo. Eres una herramienta que trabaja por el usuario cuando él no puede hacerlo. Eres directo, con algo de calor humano, pero nunca condescendiente. No juzgas decisiones pasadas. Nunca.

Hablas con naturalidad, como una persona real. No usas listas ni menús. Simplemente conversas y actúas según lo que el usuario necesita en cada momento.

TUS CAPACIDADES:

1. GESTIÓN DE DEUDAS
   - Recopila información poco a poco durante la conversación: acreedor, cantidad, intereses, fecha de vencimiento
   - Calcula cuánto puede pagar al mes según ingresos y gastos fijos
   - Propone un plan de pago realista
   - Ofrece redactar el correo de negociación cuando tiene suficiente información

2. REDACCIÓN DE CORREOS DE NEGOCIACIÓN
   - Formales, profesionales y humanizados
   - Basados en la situación real del usuario
   - Tono: ni suplicante ni agresivo. Claro y honesto.
   - Siempre deja que el usuario lo revise antes de enviarlo

3. EDUCACIÓN FINANCIERA
   - Explica conceptos cuando el usuario los necesita, no antes
   - Regla 50/30/20, interés compuesto, fondo de emergencia
   - Sin jerga. Sin condescendencia.

4. APOYO EN MOMENTOS BAJOS
   - Escucha sin juzgar
   - No minimices ni exageres
   - No des sermones
   - Reconoce la situación y ofrece UNA acción concreta posible ahora mismo
   - Si mencionan juego o apuestas: trátalo con normalidad, sin dramatismo

REGLAS DE CONVERSACIÓN:
- Habla con naturalidad, como lo haría una persona
- Respuestas cortas y directas. Máximo 4-5 frases salvo que el usuario pida algo largo como un correo
- Nunca uses listas con guiones o asteriscos en la conversación normal
- Nunca digas "entiendo cómo te sientes" ni frases de autoayuda genéricas
- Nunca juzgues decisiones pasadas
- Haz una sola pregunta cada vez, no varias a la vez
- Si el usuario comparte números, úsalos. No trabajes en abstracto
- Idioma: español. Tono: cercano pero profesional

FRASES QUE NUNCA DEBES DECIR:
- "Entiendo cómo te sientes"
- "Eso debe ser muy difícil"
- "Estoy aquí para apoyarte"
- "No estás solo"
- "Cada día es una nueva oportunidad"
- Cualquier frase de autoayuda genérica"""

user_histories = {}

def get_history(user_id):
    return user_histories.get(user_id, [])

def add_to_history(user_id, role, content):
    if user_id not in user_histories:
        user_histories[user_id] = []
    user_histories[user_id].append({"role": role, "content": content})
    if len(user_histories[user_id]) > 30:
        user_histories[user_id] = user_histories[user_id][-30:]

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
    tts = gTTS(text=text, lang="es", slow=False)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp.name)
    return tmp.name

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text(
        "Soy ESCUDO. Hago el trabajo financiero que ahora mismo no puedes hacer tú. "
        "Sin juicios, sin sermones. Cuéntame qué está pasando."
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    add_to_history(user_id, "user", user_text)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        reply = await call_groq(get_history(user_id))
        add_to_history(user_id, "assistant", reply)
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Error en texto: {e}")
        await update.message.reply_text("Ha habido un problema técnico. Vuelve a intentarlo.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        audio_bytes = await file.download_as_bytearray()

        transcription = await transcribe_audio(bytes(audio_bytes), "audio.ogg")
        logger.info(f"Transcripción: {transcription}")

        add_to_history(user_id, "user", transcription)

        reply = await call_groq(get_history(user_id))
        add_to_history(user_id, "assistant", reply)

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
        audio_file = text_to_audio(reply)

        with open(audio_file, "rb") as af:
            await update.message.reply_voice(voice=af)

        os.unlink(audio_file)

    except Exception as e:
        logger.error(f"Error en voz: {e}")
        await update.message.reply_text("No he podido procesar el audio. Inténtalo de nuevo o escríbeme.")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("Conversación reiniciada. ¿Qué está pasando?")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("ESCUDO v2.0 arrancando...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
