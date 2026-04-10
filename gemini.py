"""
gemini.py — Calls Gemini 1.5 Flash via REST API directly.
No SDK — avoids all dependency conflicts.
"""

import os
import asyncio
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-1.5-flash"
URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={GEMINI_API_KEY}"

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
    prompt = f"""KNOWLEDGE BASE:
{knowledge}

USER QUESTION: {question}

Answer using the knowledge above. Be concise."""

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 512
        }
    }

    logger.info(f"Sending to Gemini: {question[:60]}")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(URL, json=payload)
        response.raise_for_status()
        data = response.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        logger.info("Gemini response OK")
        return _safe_markdown(text)
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected Gemini response structure: {data}")
        raise RuntimeError("Failed to parse Gemini response") from e


def _safe_markdown(text: str) -> str:
    text = text.replace("**", "*")
    return text