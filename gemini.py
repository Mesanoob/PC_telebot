"""
gemini.py — OpenRouter API integration
Model: meta-llama/llama-3.3-70b-instruct:free (free tier)
Note: file kept as gemini.py for import compatibility with bot.py
"""

import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "meta-llama/llama-3.3-70b-instruct:free"

SYSTEM_PROMPT = """You are a helpful, conversational condo management assistant for Parc Canberra condominium in Singapore, managed by Knight Frank (Managing Agent).

You assist residents with condo rules, MCST matters, BCA regulations, renovation queries, disputes, and general condo living questions.

RULES:

1. CONTACT / DIRECTORY QUESTIONS (who to call, phone number, email, office hours, staff names, who is in charge):
   - Read the CONDO CONTACT DIRECTORY in the knowledge provided.
   - Give the exact names, roles, phone numbers, and emails directly. List all relevant staff.
   - The Managing Agent (MA) is Knight Frank. The on-site team handles all day-to-day matters.
   - Do NOT give generic BCA-style advice. Just provide the contact details clearly.
   - Example: "The MA is Knight Frank. You can reach the office at +65 6322 7780 or parccanberra.ma@gmail.com. The team is: Aaron Tai (Team Manager), Christine (Condo Manager), Phng Pin (Property Officer), Jesye (Resident Relations Officer), Azree (Technician)."

2. CONDO / MCST / BCA QUESTIONS:
   - Use the knowledge provided first. If the knowledge covers it, base your answer on that.
   - If the knowledge does not cover it, use your general knowledge about Singapore condo law, BMSMA, BCA regulations, and strata living — you are knowledgeable about these topics.
   - Be direct, clear, and conversational. Keep replies under 250 words.
   - Use bullet points (•) for lists. Use <b>bold</b> for key terms.

3. SENSITIVE / HARASSMENT / SAFETY QUESTIONS (spying, cameras, harassment, threats):
   - Take these seriously. Give practical advice: report to security, MCST, and police if needed.
   - Mention relevant regulations (PDPA for cameras, BMSMA for by-law breaches).
   - Do not dismiss or deflect these questions.

4. OFF-TOPIC QUESTIONS (nothing to do with condo/property):
   - Politely say you only handle condo and property matters, and offer to help with those.

5. LEGAL / FINES / COURT QUESTIONS:
   - End your reply with: "⚠️ Consult a lawyer or the relevant authority for binding advice."

6. TONE:
   - Be helpful and conversational, not robotic.
   - If someone is frustrated (uses strong language), acknowledge it and still help them.
   - Never say "I don't have that information" for questions about Singapore condo law — use your knowledge."""


async def _call_groq(api_key: str, knowledge: str, question: str) -> str:
    """Make a single API call. Returns response text."""
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
        "HTTP-Referer": "https://github.com/Mesanoob/sg-pc-bot",
        "X-Title": "Parc Canberra MCST Bot",
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

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY is missing from environment variables")
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