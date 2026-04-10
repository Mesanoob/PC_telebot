"""
gemini.py — Gemini Flash integration for MCST bot.
"""

import os
import asyncio
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

MODEL = "gemini-1.5-flash-latest"

SYSTEM_PROMPT = """You are an MCST (condo management) assistant for Singapore.
Answer questions about condo by-laws, AGMs, disputes, renovations, managing agents, and common property.

Rules:
- Be direct and concise. No fluff.
- Use the knowledge provided. Do not guess.
- If unsure, say so and refer to BCA (bca.gov.sg) or STB (stratatb.gov.sg).
- Use bullet points for lists. Bold key terms with *asterisks*.
- Keep replies under 250 words unless detail is essential.
- End with: "⚠️ Consult a lawyer or the relevant authority for binding advice." only if the question involves legal action or fines."""

_model = genai.GenerativeModel(
    model_name=MODEL,
    system_instruction=SYSTEM_PROMPT,
    generation_config={
        "temperature": 0.2,
        "max_output_tokens": 512,
    },
)


async def ask_gemini(question: str, knowledge: str) -> str:
    prompt = f"""KNOWLEDGE BASE:
{knowledge}

USER QUESTION: {question}

Answer using the knowledge above. Be concise."""

    logger.info(f"Sending to Gemini: {question[:60]}")

    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: _model.generate_content(prompt)
        )
        text = response.text.strip()
        logger.info("Gemini response OK")
        return _safe_markdown(text)
    except Exception as e:
        logger.error(f"Gemini API error: {e}", exc_info=True)
        raise


def _safe_markdown(text: str) -> str:
    text = text.replace("**", "*")
    return text