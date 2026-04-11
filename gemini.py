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


async def _call_groq(api_key: str, knowledge: str, question: str) -> str:
    """Make a single Groq API call. Returns response text."""
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
        "max_tokens": 512,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(URL, json=payload, headers=headers)
        if response.status_code != 200:
            logger.error(f"Groq API {response.status_code}: {response.text}")
            response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"].strip()


async def ask_gemini(question: str, knowledge: str) -> str:
    """Keep function name for compatibility with bot.py.
    Retries with halved knowledge if Groq returns 413 (payload too large)."""

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY is missing from environment variables")
        return "⚠️ Configuration error: API Key not found."

    logger.info(f"Sending to Groq: {question[:60]}")

    current_knowledge = knowledge
    for attempt in range(3):  # up to 3 attempts, halving content each time
        try:
            text = await _call_groq(api_key, current_knowledge, question)
            logger.info(f"Groq response OK (attempt {attempt + 1})")
            return _safe_markdown(text)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 413:
                # Payload too large — halve the knowledge and retry
                current_knowledge = current_knowledge[: len(current_knowledge) // 2]
                logger.warning(
                    f"413 Too Large on attempt {attempt + 1}. "
                    f"Retrying with {len(current_knowledge)} chars of knowledge."
                )
            else:
                raise

    # All retries exhausted
    logger.error("All Groq retries failed due to payload size.")
    return "⚠️ I couldn't process your request — the knowledge content is too large. Please try a more specific question."


def _safe_markdown(text: str) -> str:
    text = text.replace("**", "*")
    return text