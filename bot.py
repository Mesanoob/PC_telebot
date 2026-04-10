"""
SG Condo MCST Telegram Bot
Powered by Gemini Flash (free tier)
Hosted on Render free web service with keep-alive ping
"""

import os
import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from knowledge import get_relevant_knowledge
from gemini import ask_gemini

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

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


# ── Keep-alive web server ─────────────────────────────────────────
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running.")

    def log_message(self, format, *args):
        pass  # suppress HTTP access logs


def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    logger.info(f"Keep-alive web server on port {port}")
    server.serve_forever()


def start_keep_alive_ping():
    """Ping ourselves every 10 minutes so Render doesn't sleep us."""
    if not RENDER_URL:
        return  # skip when running locally

    def ping_loop():
        while True:
            try:
                urlopen(RENDER_URL)
                logger.info("Keep-alive ping sent")
            except Exception as e:
                logger.warning(f"Ping failed: {e}")
            # sleep 10 minutes
            import time
            time.sleep(600)

    t = threading.Thread(target=ping_loop, daemon=True)
    t.start()


# ── Telegram handlers ─────────────────────────────────────────────
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
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            "⚠️ Sorry, I encountered an error. Please try again shortly."
        )


# ── Main ──────────────────────────────────────────────────────────
def main():
    # Start keep-alive web server in background thread
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Start self-ping loop
    start_keep_alive_ping()

    # Start Telegram bot
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
