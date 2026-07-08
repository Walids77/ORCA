"""The LLM adapter — the ONE place that knows which model is behind the brain.

Design rule (locked Session 9): the brain's nodes NEVER call Gemini directly.
They call `ask(...)` here. When Bedrock/Claude is unblocked, we change ONLY this
file (and re-run the eval, since prompts tuned on Gemini may need small tweaks).

Temporary model = Gemini `gemini-2.5-flash`. Key lives in the git-ignored `.env`.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from google import genai

MODEL = "gemini-2.5-flash"  # the only model name in the whole brain


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    """Build the Gemini client once (reused across calls)."""
    load_dotenv()
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing from .env")
    return genai.Client(api_key=key)


def ask(prompt: str) -> str:
    """Send one prompt to the model, return the plain-text answer."""
    resp = _client().models.generate_content(model=MODEL, contents=prompt)
    return (resp.text or "").strip()
