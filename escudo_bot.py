#!/usr/bin/env python3
"""
ESCUDO - Bot de gestión financiera para Telegram
Versión 1.2 — HTTP directo a Groq
"""

import os
import logging
import httpx
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_KEY       = os.environ.get("GROQ_KEY", "")
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL     = "llama-3.3-70b-versatile"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres ESCUDO, un bot de gestión financiera diseñado específicamente para personas con problemas económicos o adicciones como la ludopatía.

QUIÉN ERES:
No eres un amigo. Eres una herramienta que trabaja por el usuario cuando él no puede hacerlo. Eres directo, con algo de calor humano, pero nunca condescendiente. No juzgas decisiones pasadas. Nunca.

TUS FUNCIONES PRINCIPALES:

1. GESTIÓN DE DEUDAS
   - Recopila: acreedor, cantidad total, intereses, fecha de vencimiento
   - Calcula cuánto puede pagar al mes según ingresos y gastos fijos
   - Crea un plan de pago realista y escalonado
   - Ofrécete siempre a redactar el correo de negociación

2. REDACCIÓN DE CORREOS DE NEGOCIACIÓN
   - Correos formales, profesionales y humanizados
   - Basados en la situación real del usuario
   - Proponen un plan de pago concreto y realista
   - Tono: ni suplicante ni agresivo. Claro y honesto.

3. EDUCACIÓN FINANCIERA
   - Regla 50/30/20
   - Cómo funciona el interés
   - Fondo de emergencia
   - Sin jerga. Sin condescendencia.

4. APOYO EN MOMENTOS BAJOS
   - Escucha sin juzgar
   - No des sermones
   - Devuelve UNA acción concreta posible ahora mismo
   - Si mencionan juego: trátalo con normalidad, redirige a la acción

REGLAS:
- Respuestas cortas. Máximo 5-6 líneas.
- Nunca digas "entiendo cómo te sientes" ni frases de autoayuda genéricas
- Nunca juzgues decisiones pasadas
- Siempre termina con UNA pregunta concreta o UNA acción específica
- Idioma: español. Tono: cercano pero profesional."""

user_histories = {}

def get_history(user_id):
    return user_histories.get(user_id, [])

def add_to_history(user_id, role, content):
    if user_id not in user_histories:
        user_histories[user_id] = []
    user_histories[user_id].append({"role": role, "content": content})
    if len(user_histories[user_id]) > 20:
        user_histories[user_id] = user_histories[user_id][-20:]

def main_keyboard():
    keyboard = [
        [KeyboardButton("💳 Gestionar mis deudas"), KeyboardButton("📧 Negociar con acreedor")],
        [KeyboardButton("📊 Educación financiera"), KeyboardButton("📈 Mi situación actual")],
        [KeyboardButton("💬 Necesito hablar"),      KeyboardButton("❓ Ayuda")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

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
        response = await client.post(GROQ_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    welcome = (
        "Soy *ESCUDO*.\n\n"
        "Hago el trabajo financiero que ahora mismo no puedes hacer tú. "
        "Sin juicios, sin sermones. Solo gestión.\n\n"
        "¿Por dónde empezamos?"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=main_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    button_map = {
        "💳 Gestionar mis deudas":  "Quiero gestionar y organizar mis deudas. Ayúdame a hacer un plan.",
        "📧 Negociar con acreedor": "Necesito que me ayudes a redactar un correo para negociar una deuda con un acreedor.",
        "📊 Educación financiera":  "Quiero aprender a gestionar mejor mi dinero. ¿Por dónde empiezo?",
        "📈 Mi situación actual":   "Quiero revisar mi situación financiera actual y ver cómo estoy.",
        "💬 Necesito hablar":       "Estoy en un momento difícil y necesito hablar.",
        "❓ Ayuda":                 "¿Qué puedes hacer por mí exactamente?"
    }

    message = button_map.get(user_text, user_text)
    add_to_history(user_id, "user", message)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        reply = await call_groq(get_history(user_id))
        add_to_history(user_id, "assistant", reply)
        await update.message.reply_text(reply, reply_markup=main_keyboard())
    except Exception as e:
        logger.error(f"Error en API: {e}")
        await update.message.reply_text(
            "Ha habido un problema técnico. Vuelve a intentarlo en un momento.",
            reply_markup=main_keyboard()
        )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("Conversación reiniciada. ¿En qué puedo ayudarte?", reply_markup=main_keyboard())

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("ESCUDO arrancando...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
