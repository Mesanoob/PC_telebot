"""
SG Condo MCST Telegram Bot
"""

import os
import sys
import logging
import threading
import time
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen

from dotenv import load_dotenv
load_dotenv()

# ── Rate limiting ─────────────────────────────────────────────────
# Max messages per user within the time window
RATE_LIMIT = 5          # max requests
RATE_WINDOW = 60        # per N seconds
MAX_MSG_LENGTH = 500    # max characters per user message

_user_timestamps: dict[int, list[float]] = defaultdict(list)

def is_rate_limited(user_id: int) -> bool:
    now = time.time()
    timestamps = _user_timestamps[user_id]
    # Drop timestamps outside the window
    _user_timestamps[user_id] = [t for t in timestamps if now - t < RATE_WINDOW]
    if len(_user_timestamps[user_id]) >= RATE_LIMIT:
        return True
    _user_timestamps[user_id].append(now)
    return False

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
# Suppress httpx logs — they expose the Telegram token in the URL
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ── Validate env vars ─────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not TELEGRAM_TOKEN:
    logger.error("MISSING: TELEGRAM_TOKEN")
    sys.exit(1)
if not GROQ_API_KEY:
    logger.error("MISSING: GROQ_API_KEY")
    sys.exit(1)

logger.info("ENV vars OK")

# ── Group chat behaviour ───────────────────────────────────────────
# Set to True  → bot answers ALL messages in group (requires Group Privacy OFF in BotFather)
# Set to False → bot only answers when @mentioned or when someone replies to the bot
GROUP_RESPOND_TO_ALL = True

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
    await update.message.reply_text(WELCOME, parse_mode="HTML")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP, parse_mode="HTML")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_type = update.message.chat.type
    user_msg = update.message.text.strip()
    bot_username = context.bot.username

    # ── Group chat filtering ───────────────────────────────────────
    if chat_type in ("group", "supergroup"):
        if GROUP_RESPOND_TO_ALL:
            # Respond to everything — requires Group Privacy OFF in BotFather
            pass
        else:
            # Only respond when @mentioned or someone replies to the bot
            mentioned = bot_username and f"@{bot_username}" in user_msg
            replied_to_bot = (
                update.message.reply_to_message is not None
                and update.message.reply_to_message.from_user is not None
                and update.message.reply_to_message.from_user.username == bot_username
            )
            if not mentioned and not replied_to_bot:
                return
            # Strip the @mention from the message before processing
            if mentioned:
                user_msg = user_msg.replace(f"@{bot_username}", "").strip()

    if not user_msg:
        return

    user_id = update.message.from_user.id

    # Rate limit check
    if is_rate_limited(user_id):
        await update.message.reply_text(
            "⏳ You're sending messages too quickly. Please wait a moment before trying again."
        )
        return

    # Message length cap
    if len(user_msg) > MAX_MSG_LENGTH:
        await update.message.reply_text(
            f"⚠️ Your message is too long (max {MAX_MSG_LENGTH} characters). Please shorten your question."
        )
        return

    await update.message.chat.send_action("typing")
    try:
        knowledge = get_relevant_knowledge(user_msg)
        answer = await ask_gemini(user_msg, knowledge)
        await update.message.reply_text(answer, parse_mode="HTML")
    except Exception as e:
        logger.error(f"handle_message error: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Sorry, I encountered an error. Please try again shortly."
        )


# ── Error handler ────────────────────────────────────────────────
async def error_handler(update, context):
    error = context.error
    # Suppress Conflict errors — happen briefly during redeploys
    if "Conflict" in str(error):
        logger.warning("Conflict error (old instance still shutting down) — ignoring")
        return
    logger.error(f"Telegram error: {error}", exc_info=context.error)


# ── Main ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    threading.Thread(target=run_ping_loop, daemon=True).start()

    logger.info("Starting bot...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    logger.info("Polling started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)