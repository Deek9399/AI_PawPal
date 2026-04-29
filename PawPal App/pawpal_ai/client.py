from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from openai import APIStatusError, OpenAI, RateLimitError

from pawpal_ai.config import LLMSettings, get_llm_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin Groq / OpenAI-compatible chat wrapper."""

    def __init__(self, settings: Optional[LLMSettings] = None):
        self.settings = settings or get_llm_settings()
        self._client: Optional[OpenAI] = None

    def _ensure(self) -> OpenAI:
        if not self.settings.api_key:
            raise ValueError("Missing API key: set GROQ_API_KEY or OPENAI_API_KEY")
        if self._client is None:
            self._client = OpenAI(
                api_key=self.settings.api_key,
                base_url=self.settings.base_url,
            )
        return self._client

    def chat(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        model: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        m = model or self.settings.model
        client = self._ensure()
        kwargs: Dict[str, Any] = {
            "model": m,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        try:
            resp = client.chat.completions.create(**kwargs)
            return (resp.choices[0].message.content or "").strip()
        except RateLimitError as e:
            logger.warning("Groq rate limit: %s", e)
            raise RuntimeError(
                "API rate limit reached. Wait a moment or check Groq free-tier limits on console.groq.com."
            ) from e
        except APIStatusError as e:
            if getattr(e, "status_code", None) == 429:
                raise RuntimeError(
                    "API rate limit (HTTP 429). Try again shortly or check Groq quota."
                ) from e
            logger.exception("LLM API error")
            raise RuntimeError(f"API error: {e}") from e

    def available(self) -> bool:
        return bool(self.settings.api_key)
