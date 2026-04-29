import os
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    # Streamlit cwd may not be repo root—load .env from project directory explicitly
    load_dotenv(_REPO_ROOT / ".env")
    load_dotenv()
except ImportError:
    pass

DEFAULT_GROQ_BASE = "https://api.groq.com/openai/v1"
# Common Groq model; user can override via env (list at https://console.groq.com/)
DEFAULT_MODEL = "llama-3.1-8b-instant"


@dataclass
class LLMSettings:
    api_key: Optional[str]
    base_url: str
    model: str


def _get_streamlit_secrets() -> Any:
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            return st.secrets
    except Exception:
        pass
    return None


def get_llm_settings() -> LLMSettings:
    """Resolve Groq / OpenAI-compatible settings from env and optional Streamlit secrets."""
    secrets = _get_streamlit_secrets()
    def pick(*keys: str) -> Optional[str]:
        for k in keys:
            v = os.environ.get(k)
            if v:
                return v
            if secrets is not None:
                try:
                    v = secrets.get(k)  # type: ignore[union-attr]
                    if v:
                        return str(v)
                except Exception:
                    pass
        return None

    api_key = pick("GROQ_API_KEY", "OPENAI_API_KEY")
    base = pick("OPENAI_BASE_URL", "GROQ_BASE_URL") or DEFAULT_GROQ_BASE
    model = pick("OPENAI_MODEL", "GROQ_MODEL") or DEFAULT_MODEL
    return LLMSettings(api_key=api_key, base_url=base.rstrip("/"), model=model)
