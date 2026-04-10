"""
gemini.py — Gemini Flash integration for MCST bot.
Optimised for Gemini 1.5 Flash free tier: lean prompts, direct answers.
"""

import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()  # loads .env file when running locally; ignored on Render

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

MODEL = "gemini-1.5-flash"

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
    """Send question + relevant knowledge to Gemini and return answer."""
    prompt = f"""KNOWLEDGE BASE:
{knowledge}

USER QUESTION: {question}

Answer using the knowledge above. Be concise."""

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: _model.generate_content(prompt)
    )

    text = response.text.strip()

    # Telegram Markdown safety: escape unmatched underscores
    # (Gemini sometimes outputs markdown that breaks Telegram)
    return _safe_markdown(text)


def _safe_markdown(text: str) -> str:
    """Light cleanup to keep Telegram MarkdownV1 happy."""
    # Replace ** bold with * bold (Telegram v1)
    text = text.replace("**", "*")
    return text
