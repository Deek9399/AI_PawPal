"""PawPal+ AI layer: Groq client, RAG, guardrails, orchestration."""

from pawpal_ai.config import get_llm_settings
from pawpal_ai.client import LLMClient
from pawpal_ai.trace import TraceLog, TraceEntry

__all__ = [
    "get_llm_settings",
    "LLMClient",
    "TraceLog",
    "TraceEntry",
]
