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

SYSTEM_PROMPT = """You are a condo management assistant for a Singapore condominium.
You answer questions about condo rules, MCST matters, BCA regulations, and provide contact details.

STRICT RULES — follow these exactly:

1. CONTACT QUESTIONS (phone, number, email, who to call, office hours, staff names):
   - Look in the CONDO CONTACT DIRECTORY section of the knowledge provided.
   - Copy the exact phone number, email, name, or hours directly from that section.
   - Do NOT give generic advice. Do NOT mention BCA guidelines or best practices.
   - Example good answer: "The MA office number is +65 6322 7780. Email: parccanberra.ma@gmail.com"
   - Example bad answer: "The MA contact should be in the agreement per BCA guidelines..."

2. KNOWLEDGE-BASED QUESTIONS (by-laws, AGM, renovation rules, disputes):
   - Answer using only the knowledge provided. Do not guess.
   - Be direct and concise. No fluff. Keep replies under 250 words.
   - Bold key terms with <b>bold</b> HTML tags.
   - Use bullet points with • for lists.

3. UNKNOWN QUESTIONS:
   - If the answer is not in the knowledge provided, say:
     "I don't have that information. Please contact the MA office at +65 6322 7780 or email parccanberra.ma@gmail.com"

4. LEGAL / FINES QUESTIONS:
   - End your reply with: "⚠️ Consult a lawyer or the relevant authority for binding advice."

5. NEVER add generic recommendations, best practices, or filler text when a specific answer exists in the knowledge."""


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