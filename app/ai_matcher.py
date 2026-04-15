"""
ai_matcher.py — Claude-powered match insight generator.

Think of this as a wise friend who knows both people and can articulate exactly
why they would enjoy spending time together — grounded in their real shared interests.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Optional

import anthropic

logger = logging.getLogger(__name__)

_client: Optional[anthropic.AsyncAnthropic] = None

# Stable system prompt — placed under cache_control so it is reused across
# every call to this function, reducing both latency and cost.
_SYSTEM_PROMPT = """You are a warm, friendly social connector for a proximity-based matching app.

Given a list of match candidates for a user, write a short (2 sentences max), specific,
and upbeat compatibility insight for each match explaining why they would enjoy meeting.

Rules:
- Be concrete — mention the actual shared interests by name, never say "common interests"
- Write in second person: "You and [name]..."
- End each insight with one specific icebreaker action or question
- Never mention scores, algorithms, or distance
- Keep each insight under 50 words

Respond ONLY with a JSON object in this exact format — no markdown, no extra text:
{
  "insights": [
    {"user_id": 123, "insight": "You and Alex both love hiking and coding..."},
    {"user_id": 456, "insight": "You and Sam share a passion for..."}
  ]
}"""


def _get_client() -> anthropic.AsyncAnthropic:
    """Return the shared async client, created lazily on first use."""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set — AI match insights are disabled."
            )
        _client = anthropic.AsyncAnthropic(api_key=api_key)
    return _client


def _format_distance(km: float) -> str:
    """Convert kilometres to a human-readable distance string."""
    return f"{round(km * 1000)}m" if km < 1 else f"{km:.2f}km"


async def generate_match_insights(
    user_name: str,
    user_interests: List[str],
    matches: List[dict],
) -> Dict[int, str]:
    """
    Call Claude once with all match data and return a mapping of user_id → insight.

    Uses a single API call for all matches (more efficient than one per match).
    The system prompt is cached with ephemeral cache_control so repeated calls
    within 5 minutes skip re-processing those tokens.

    Falls back to an empty dict on any failure — AI insights are optional.
    """
    if not matches:
        return {}

    try:
        client = _get_client()
    except RuntimeError as exc:
        logger.info("%s", exc)
        return {}

    match_lines = "\n".join(
        f'- user_id={m["user_id"]}, name="{m["name"]}", '
        f'shared=[{", ".join(m["shared_interests"])}], '
        f'distance={_format_distance(m["distance_km"])}'
        for m in matches
    )

    user_prompt = (
        f'Requesting user: {user_name} (interests: {", ".join(user_interests)})\n\n'
        f"Candidates:\n{match_lines}\n\n"
        "Generate an insight for each candidate listed above."
    )

    try:
        response = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    # Cache the stable system prompt — saves ~0.9× cost on repeat calls
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = next(
            (block.text for block in response.content if block.type == "text"), ""
        ).strip()

        data = json.loads(text)
        return {item["user_id"]: item["insight"] for item in data.get("insights", [])}

    except json.JSONDecodeError as exc:
        logger.warning("AI insights: non-JSON response from Claude — %s", exc)
        return {}
    except anthropic.APIError as exc:
        logger.warning("AI insights: Anthropic API error — %s", exc)
        return {}
    except Exception as exc:
        logger.warning("AI insights: unexpected error — %s", exc)
        return {}
