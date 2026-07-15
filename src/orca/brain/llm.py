"""The LLM adapter — the ONE place that knows which model is behind the brain.

Design rule (locked Session 9): the brain's nodes NEVER call Gemini directly.
They call `ask(...)` here. When Bedrock/Claude is unblocked, we change ONLY this
file (and re-run the eval, since prompts tuned on Gemini may need small tweaks).

Temporary model = Gemini `gemini-2.5-flash`. Key lives in the git-ignored `.env`.

Token/cost meter (roadmap item #20, added Session 14): every call through this
door is metered — tokens in/out as reported by the PROVIDER ITSELF (not our
estimate), converted to $ by the price table below. We count here because every
LLM call passes through this one file, so the meter survives the Bedrock swap
(only the price table changes) and automatically covers new nodes (router,
workers) the day they're added.
"""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv
from google import genai

MODEL = "gemini-2.5-flash"  # the only model name in the whole brain

# Paid-tier list prices, USD per MILLION tokens (ai.google.dev, checked 2026-07-10).
# We run on the FREE tier today — actual spend is $0; the token counts are real and
# the $ column shows what each answer WOULD cost on the paid tier. Billing needs OUR
# numbers, not a provider dashboard (item #20).
PRICES_PER_MTOK = {
    "gemini-2.5-flash": {"in": 0.30, "out": 2.50},
}


@dataclass
class LlmCall:
    """One LLM call's spending record."""

    purpose: str      # which brain step made the call (e.g. "combine", "numbers-form")
    model: str
    tokens_in: int    # prompt tokens, as reported by the provider
    tokens_out: int   # answer tokens INCLUDING hidden "thinking" tokens (billed as output)
    tokens_total_reported: int = 0  # the provider's own total — acceptance check: in+out must equal it

    @property
    def cost_usd(self) -> float:
        p = PRICES_PER_MTOK.get(self.model, {"in": 0.0, "out": 0.0})
        return (self.tokens_in * p["in"] + self.tokens_out * p["out"]) / 1_000_000


_calls: list[LlmCall] = []


def reset_meter() -> None:
    """Start a fresh spending record (evals call this before each question)."""
    _calls.clear()


def meter_calls() -> list[LlmCall]:
    """Every call since the last reset, in order."""
    return list(_calls)


def meter_summary() -> dict:
    """Totals since the last reset: calls · tokens in · tokens out · cost in USD."""
    return {
        "calls": len(_calls),
        "tokens_in": sum(c.tokens_in for c in _calls),
        "tokens_out": sum(c.tokens_out for c in _calls),
        "cost_usd": sum(c.cost_usd for c in _calls),
    }


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    """Build the Gemini client once (reused across calls)."""
    load_dotenv()
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing from .env")
    return genai.Client(api_key=key)


def _meter(resp, purpose: str) -> None:
    """Record one call from the provider's own usage report (never our estimate)."""
    usage = getattr(resp, "usage_metadata", None)
    tokens_in = getattr(usage, "prompt_token_count", 0) or 0
    tokens_out = (getattr(usage, "candidates_token_count", 0) or 0) + (
        getattr(usage, "thoughts_token_count", 0) or 0
    )
    _calls.append(
        LlmCall(
            purpose=purpose,
            model=MODEL,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            tokens_total_reported=getattr(usage, "total_token_count", 0) or 0,
        )
    )


def ask(prompt: str, purpose: str = "", temperature: float | None = None) -> str:
    """Send one prompt to the model, return the plain-text answer (metered).

    temperature: the model's randomness dial. None = provider default; 0.0 =
    always the most likely answer — used by steps whose verdicts must
    REPRODUCE run after run (the no-lucky-passes rule), e.g. gate Layer 2.
    """
    config = None
    if temperature is not None:
        from google.genai import types

        config = types.GenerateContentConfig(temperature=temperature)
    resp = _client().models.generate_content(model=MODEL, contents=prompt, config=config)
    _meter(resp, purpose)
    return (resp.text or "").strip()


def ask_with_image(prompt: str, image_bytes: bytes, mime_type: str = "image/png",
                   purpose: str = "") -> str:
    """Send one prompt PLUS one image to the model (vision), metered like any call.

    Same one-door rule: ingestion's photo captioning calls this, never the
    provider directly — the Bedrock/Claude swap stays a one-file change.
    """
    from google.genai import types

    resp = _client().models.generate_content(
        model=MODEL,
        contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt],
    )
    _meter(resp, purpose)
    return (resp.text or "").strip()
