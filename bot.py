"""
SG Condo MCST Telegram Bot
Powered by Gemini Flash (free tier)
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from knowledge import get_relevant_knowledge
from gemini import ask_gemini

load_dotenv()  # loads .env file when running locally; ignored on Render

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

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

    # Show typing indicator
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


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
