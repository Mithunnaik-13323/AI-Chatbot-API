from typing import List, Dict
from openai import OpenAI, OpenAIError
from fastapi import HTTPException, status

from app.config import settings

_client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

SYSTEM_PROMPT = (
    "You are a helpful, friendly AI assistant. Keep answers concise and accurate. "
    "If you are unsure about something, say so instead of guessing."
)


async def generate_reply(history: List[Dict[str, str]], user_message: str) -> str:
    """
    Generate an assistant reply given prior conversation history.

    history: list of {"role": "user"|"assistant", "content": str}, oldest first.
    """
    if _client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI provider is not configured. Set OPENAI_API_KEY in your environment.",
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        response = _client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0.7,
            max_tokens=600,
        )
        return response.choices[0].message.content.strip()
    except OpenAIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI provider error: {exc}",
        )
