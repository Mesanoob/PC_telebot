"""
SG Condo MCST Telegram Bot
"""

import os
import sys
import asyncio
import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Validate env vars ─────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_TOKEN:
    logger.error("MISSING: TELEGRAM_TOKEN")
    sys.exit(1)
if not GEMINI_API_KEY:
    logger.error("MISSING: GEMINI_API_KEY")
    sys.exit(1)

logger.info("ENV vars OK")

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from knowledge import get_relevant_knowledge
from gemini import ask_gemini

logger.info("All imports OK")

RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
PORT = int(os.environ.get("PORT", 8080))


# ── Keep-alive web server ─────────────────────────────────────────
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running.")
    def log_message(self, format, *args):
        pass

def run_web_server():
    server = HTTPServer(("0.0.0.0", PORT), PingHandler)
    logger.info(f"Web server on port {PORT}")
    server.serve_forever()

def run_ping_loop():
    if not RENDER_URL:
        return
    time.sleep(60)
    while True:
        try:
            urlopen(RENDER_URL, timeout=10)
            logger.info("Ping OK")
        except Exception as e:
            logger.warning(f"Ping failed: {e}")
        time.sleep(600)


# ── Telegram handlers ─────────────────────────────────────────────
WELCOME = (
    "👋 *SG Condo MCST Bot*\n\n"
    "Ask me anything about condo management in Singapore:\n"
    "• By-laws & enforcement\n"
    "• AGM/EGM procedures\n"
    "• Renovation rules\n"
    "• Dispute resolution\n"
    "• Managing agents\n"
    "• Common property\n\n"
    "Type your question to get started."
)

HELP = (
    "💡 *What I can help with:*\n\n"
    "🏢 *MCST rules* — by-laws, enforcement, fines\n"
    "📋 *Meetings* — AGM/EGM process, voting, quorum\n"
    "🔨 *Renovations* — approval, working hours, permits\n"
    "🤝 *Disputes* — STB, mediation, court options\n"
    "👔 *Managing agents* — roles, contracts, duties\n"
    "🏊 *Common property* — maintenance, access, repairs\n"
    "💧 *Water seepage* — responsibility, claims\n"
    "📜 *Motions* — how to write, resolution types\n\n"
    "Just type your question!"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text.strip()
    if not user_msg:
        return
    await update.message.chat.send_action("typing")
    try:
        knowledge = get_relevant_knowledge(user_msg)
        answer = await ask_gemini(user_msg, knowledge)
        await update.message.reply_text(answer, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"handle_message error: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Sorry, I encountered an error. Please try again shortly."
        )


# ── Main ──────────────────────────────────────────────────────────
async def run_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot polling started.")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # Start keep-alive web server in background thread
    threading.Thread(target=run_web_server, daemon=True).start()
    threading.Thread(target=run_ping_loop, daemon=True).start()

    # Python 3.14 requires explicitly creating the event loop
    logger.info("Starting event loop...")
    try:
        asyncio.run(run_bot())
    except Exception as e:
        logger.error(f"FATAL: {e}", exc_info=True)
        sys.exit(1)