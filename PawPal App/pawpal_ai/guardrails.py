import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str
    user_message: str


_DIAGNOSE_PATTERNS = [
    re.compile(r"\bdiagnos(e|is|ing)\b", re.I),
    re.compile(r"\bwhat('?s| is) wrong with my (pet|dog|cat)\b", re.I),
    re.compile(r"\b(is this )?infection\b", re.I),
    re.compile(r"\bcancer\b", re.I),
]

_DOSE_PATTERNS = [
    re.compile(r"\b(how much|what dose|dosage|mg|ml)\b.*\b(insulin|med|medication|drug|pill)\b", re.I),
    re.compile(r"\bprescribe\b", re.I),
]

_EMERGENCY_PATTERNS = [
    re.compile(r"\b(can'?t breathe|not breathing|unconscious| seizur)\b", re.I),
    re.compile(r"\bemergency\b", re.I),
]


def check_user_input(text: str) -> GuardrailResult:
    """
    Block or redirect unsafe veterinary/medical requests.
    PawPal+ is not a substitute for a veterinarian.
    """
    t = (text or "").strip()
    if not t:
        return GuardrailResult(True, "empty", "")

    for p in _EMERGENCY_PATTERNS:
        if p.search(t):
            return GuardrailResult(
                False,
                "emergency",
                "This sounds like it could be an emergency. Contact your veterinarian or an emergency clinic immediately. PawPal+ cannot help with emergencies.",
            )

    for p in _DOSE_PATTERNS:
        if p.search(t):
            return GuardrailResult(
                False,
                "dosing",
                "PawPal+ cannot provide medication dosing or prescription advice. Please consult your veterinarian for any medication questions.",
            )

    for p in _DIAGNOSE_PATTERNS:
        if p.search(t):
            return GuardrailResult(
                False,
                "diagnosis",
                "PawPal+ cannot diagnose medical conditions. If you are worried about your pet's health, please contact a licensed veterinarian.",
            )

    return GuardrailResult(True, "ok", "")


def quick_refusal_keywords(text: str) -> Optional[str]:
    """Lightweight check used in diagnostics (mirrors main guardrail themes)."""
    r = check_user_input(text)
    if not r.allowed:
        return r.reason
    return None
