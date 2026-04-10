"""
gemini.py — Groq API integration (free tier, no SDK needed)
Model: llama-3.1-8b-instant — fast, free, capable
Note: file kept as gemini.py for import compatibility with bot.py
"""

import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """You are an MCST (condo management) assistant for Singapore.
Answer questions about condo by-laws, AGMs, disputes, renovations, managing agents, and common property.

Rules:
- Be direct and concise. No fluff.
- Use the knowledge provided. Do not guess.
- If unsure, say so and refer to BCA (bca.gov.sg) or STB (stratatb.gov.sg).
- Use bullet points for lists. Bold key terms with *asterisks*.
- Keep replies under 250 words unless detail is essential.
- End with: "⚠️ Consult a lawyer or the relevant authority for binding advice." only if the question involves legal action or fines."""


async def ask_gemini(question: str, knowledge: str) -> str:
    """Keep function name for compatibility with bot.py"""
    user_content = f"""KNOWLEDGE BASE:
{knowledge}

USER QUESTION: {question}

Answer using the knowledge above. Be concise."""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2,
        "max_tokens": 512
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }

    GROQ_API_KEY = os.environ["GROQ_API_KEY"]
    logger.info(f"Sending to Groq: {question[:60]}")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(URL, json=payload, headers=headers)
        if response.status_code != 200:
            logger.error(f"Groq API {response.status_code}: {response.text}")
            response.raise_for_status()
        data = response.json()

    try:
        text = data["choices"][0]["message"]["content"].strip()
        logger.info("Groq response OK")
        return _safe_markdown(text)
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected Groq response: {data}")
        raise RuntimeError("Failed to parse Groq response") from e


def _safe_markdown(text: str) -> str:
    text = text.replace("**", "*")
    return text