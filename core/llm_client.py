from __future__ import annotations

import logging
import asyncio
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.OPENROUTER_BASE_URL,
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://interview-coach-bot.tg",
                "X-Title": "Interview Coach Bot",
            },
            timeout=45.0,
        )
    return _client


async def chat_completion(
    messages: list[dict],
    model: Optional[str] = None,
    max_tokens: int = 1500,
    retries: int = 3,
) -> str:
    if model is None:
        model = settings.FREE_MODEL

    client = _get_client()

    for attempt in range(retries):
        try:
            resp = await client.post(
                "/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPStatusError as e:
            logger.error("LLM HTTP error %s: %s", e.response.status_code, e.response.text)
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                raise
        except asyncio.TimeoutError as e:
            logger.warning("LLM timeout attempt %d", attempt)
            if attempt < retries - 1:
                await asyncio.sleep(2)
            else:
                raise
        except Exception as e:
            logger.error("LLM error attempt %d: %s", attempt, e)
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                raise

    raise RuntimeError("LLM failed after retries")
