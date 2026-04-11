"""
gemini.py — OpenRouter API integration
Model: openrouter/free (Automatically picks the best available free model)
"""

import os
import logging
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Auto-router picks the most available free model to avoid congestion
URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"

SYSTEM_PROMPT = """You are a helpful, conversational condo management assistant for Parc Canberra condominium in Singapore, managed by Knight Frank (Managing Agent).

You assist residents with condo rules, MCST matters, BCA regulations, renovation queries, disputes, and general condo living questions.

RULES:

1. CONTACT / DIRECTORY QUESTIONS:
   - Read the CONDO CONTACT DIRECTORY in the knowledge provided.
   - Give the exact names, roles, phone numbers, and emails directly.
   - The Managing Agent (MA) is Knight Frank.

2. CONDO / MCST / BCA QUESTIONS:
   - Use the knowledge provided first. 
   - Be direct, clear, and conversational. Keep replies under 250 words.
   - Use bullet points (•) for lists. Use <b>bold</b> for key terms.

3. SENSITIVE / HARASSMENT / SAFETY QUESTIONS:
   - Take these seriously. Give practical advice: report to security, MCST, and police if needed.

4. OFF-TOPIC QUESTIONS:
   - Politely say you only handle condo and property matters.

5. LEGAL / FINES / COURT QUESTIONS:
   - End your reply with: "⚠️ Consult a lawyer or the relevant authority for binding advice."

6. TONE:
   - Be helpful and conversational, not robotic."""


async def _call_llm(api_key: str, knowledge: str, question: str) -> str:
    """Make a single API call to OpenRouter with structural safety checks."""
    user_content = f"KNOWLEDGE BASE:\n{knowledge}\n\nUSER QUESTION: {question}\n\nAnswer using the knowledge above. Be concise."

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
        "Authorization": f"Bearer {api_key.strip()}",
        "HTTP-Referer": "https://github.com/Mesanoob/sg-pc-bot",
        "X-Title": "Parc Canberra MCST Bot",
    }

    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(URL, json=payload, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"OpenRouter API {response.status_code}: {response.text}")
            response.raise_for_status()
        
        data = response.json()

    # ── SAFETY CHECK ────────────────────────────────────────────────
    # Prevents 'NoneType' object has no attribute 'strip'
    try:
        choices = data.get("choices")
        if not choices or len(choices) == 0:
            logger.error(f"OpenRouter returned no choices: {data}")
            return "⚠️ The AI service is currently unresponsive. Please try again in a few seconds."
            
        content = choices[0].get("message", {}).get("content")
        
        if content is None:
            logger.error(f"OpenRouter returned empty content: {data}")
            return "⚠️ The AI provider returned an empty response. Please try rephrasing your question."
        
        return content.strip()
        
    except (KeyError, IndexError) as e:
        logger.error(f"Malformed response structure: {e} | Data: {data}")
        return "⚠️ I'm having trouble reading the AI's response. Please try again."


async def ask_gemini(question: str, knowledge: str) -> str:
    """Handles retries for payload size (413) and rate limits (429)."""

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY is missing from environment variables")
        return "⚠️ Configuration error: API Key not found."

    logger.info(f"Sending request to OpenRouter: {question[:60]}")

    current_knowledge = knowledge
    for attempt in range(3):
        try:
            text = await _call_llm(api_key, current_knowledge, question)
            logger.info(f"Response OK (attempt {attempt + 1})")
            return _safe_markdown(text)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 413:
                # Payload too large — reduce context size and retry
                current_knowledge = current_knowledge[: len(current_knowledge) // 2]
                logger.warning(f"413 Too Large. Retrying with reduced knowledge.")
                continue

            elif e.response.status_code == 429:
                # Rate limited — wait and try again
                wait_time = 3 + (attempt * 3)
                logger.warning(f"Rate limited (429). Waiting {wait_time}s before retry {attempt + 1}...")
                await asyncio.sleep(wait_time)
                continue
            
            else:
                logger.error(f"API Error: {e.response.status_code}")
                raise

    return "⚠️ The service is currently very busy. Please try your question again in a minute."


def _safe_markdown(text: str) -> str:
    """Basic cleanup for Telegram compatibility."""
    # Convert bold markers if necessary and ensure basic consistency
    text = text.replace("**", "*")
    return text