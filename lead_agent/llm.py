"""Thin wrapper around the Anthropic API, with a JSON-mode helper.

Every reasoning step in the agent (profiling, scoring, drafting) goes
through here so retry/parsing logic lives in exactly one place.
"""
import json
import re
from typing import Any, Dict, Optional

import anthropic

from . import config

_client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file "
                "(see .env.example)."
            )
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def ask(system: str, user: str, max_tokens: int = config.MAX_TOKENS) -> str:
    """Single-turn completion, returns the raw text response."""
    client = get_client()
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def ask_json(system: str, user: str, max_tokens: int = config.MAX_TOKENS) -> Dict[str, Any]:
    """Completion where the system prompt requires a JSON-only response.

    Strips markdown code fences defensively and raises a clear error on
    malformed output rather than silently returning garbage.
    """
    raw = ask(system, user, max_tokens=max_tokens)
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Model did not return valid JSON. Raw response:\n{raw}"
        ) from exc
