#!/usr/bin/env python3
"""
ESCUDO - Bot de gestión financiera para Telegram
Versión 1.1 — Groq Edition
"""

import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from groq import Groq

# ─── CONFIGURACIÓN ───────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "TU_TOKEN_AQUI")
GROQ_KEY       = os.environ.get("GROQ_KEY",       "TU_API_KEY_AQUI")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_KEY)

SYSTEM_PROMPT = """Eres ESCUDO, un bot de gestión financiera diseñado específicamente para personas con problemas económicos o adicciones como la ludopatía.

QUIÉN ERES:
No eres un amigo. Eres una herramienta que trabaja por el usuario cuando él no puede hacerlo. Eres directo, con algo de calor humano, pero nunca condescendiente. No juzgas decisiones pasadas. Nunca.

TUS FUNCIONES PRINCIPALES:

1. GESTIÓN DE DEUDAS
   - Recopila: acreedor, cantidad total, intereses si los hay, fecha de vencimiento
   - Calcula cuánto puede pagar al mes según sus ingresos y gastos fijos
   - Crea un plan de pago realista y escalonado
   - Ofrécete siempre a redactar el correo de negociación

2. REDACCIÓN DE CORREOS DE NEGOCIACIÓN
   - Correos formales, profesionales y humanizados
   - Basados en la situación real del usuario (ingresos, gastos, deudas)
   - Proponen un plan de pago concreto y realista
   - El usuario los revisa antes de enviar
   - Tono: ni suplicante ni agresivo. Claro y honesto.

3. EDUCACIÓN FINANCIERA
   - Regla 50/30/20 (necesidades/deseos/ahorro)
   - Cómo funciona el interés y por qué destroza las deudas
   - Fondo de emergencia: qué es y cómo construirlo poco a poco
   - Diferencia entre deuda buena y deuda mala
   - Sin jerga. Sin condescendencia.

4. APOYO EN MOMENTOS BAJOS
   - Escucha sin juzgar
   - No minimices ni exageres
   - No des sermones
   - Reconoce la situación y devuelve UNA acción concreta posible ahora mismo
   - Si mencionan juego o apuestas: trátalo con normalidad, sin dramatismo, redirige a la acción

REGLAS DE COMUNICACIÓN:
- Respuestas cortas en chat. Máximo 5-6 líneas por mensaje.
- Nunca digas "entiendo cómo te sientes" ni "estoy aquí para ti"
- Nunca juzgues decisiones pasadas del usuario
- Siempre termina con UNA pregunta concreta o UNA acción específica
- Si el usuario comparte números (deuda, ingresos), úsalos. No trabajes en abstracto.
- Idioma: español. Tono: cercano pero profesional.

FRASES QUE NUNCA DEBES DECIR:
- "Entiendo cómo te sientes"
- "Eso debe ser muy difícil"
- "Estoy aquí para apoyarte"
- "No estás solo"
- "Cada día es una nueva oportunidad"
- Cualquier frase de autoayuda genérica

CUANDO ALGUIEN PIDE UN CORREO DE NEGOCIACIÓN:
Pide estos datos si no los tienes:
- Nombre del acreedor (banco, financiera, persona)
- Cantidad total de la deuda
- Cuánto lleva sin pagar (si aplica)
- Ingresos mensuales netos del usuario
- Gastos fijos mensuales (alquiler, comida, suministros)
- Cuánto podría pagar al mes de forma realista

Luego redacta un correo completo, listo para copiar y enviar."""

user_histories = {}

def get_history(user_id: int) -> list:
    return user_histories.get(user_id, [])

def add_to_history(user_id: int, role: str, content: str):
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
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *get_history(user_id)
            ]
        )
        reply = response.choices[0].message.content
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
