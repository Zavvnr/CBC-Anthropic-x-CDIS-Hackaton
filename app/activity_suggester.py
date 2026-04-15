"""
activity_suggester.py — Maps shared interest tags to suggested activities.

Think of it as a recipe book: the ingredients are the interests two people
share, and the output is a list of things they could cook up together right now.
"""

from __future__ import annotations

from typing import Dict, List


# ---------------------------------------------------------------------------
# Master interest → activities mapping.
# Keys are lowercase normalised tags (matching what models.py produces).
# Add new tags here without touching any other module.
# ---------------------------------------------------------------------------

INTEREST_ACTIVITIES: Dict[str, List[str]] = {
    "gym": ["workout together", "spot each other", "try a new class"],
    "fitness": ["workout together", "go for a run", "try a new class"],
    "running": ["go for a run", "train for a race", "explore a new route"],
    "yoga": ["yoga session", "stretch together", "meditation break"],
    "cycling": ["bike ride", "explore new trails", "spin class"],
    "swimming": ["swim laps together", "open water swim", "water polo"],
    "cs": ["pair program", "hackathon", "LeetCode session", "code review"],
    "coding": ["pair program", "hackathon", "LeetCode session", "code review"],
    "programming": ["pair program", "hackathon", "build a side project"],
    "ai": ["discuss recent papers", "build an AI demo", "hackathon"],
    "ml": ["discuss recent papers", "run experiments together", "Kaggle competition"],
    "music": ["jam session", "playlist swap", "concert"],
    "guitar": ["jam session", "learn a new song", "open mic night"],
    "piano": ["duet practice", "learn a piece together", "concert"],
    "singing": ["karaoke", "choir rehearsal", "song-writing session"],
    "gaming": ["co-op session", "tournament", "game review"],
    "chess": ["friendly match", "tactics puzzle session", "tournament"],
    "reading": ["book club", "swap recommendations", "silent reading session"],
    "writing": ["writing sprint", "swap drafts for feedback", "open-mic poetry"],
    "photography": ["photo walk", "photo critique session", "exhibition visit"],
    "art": ["life drawing", "gallery visit", "sketch together"],
    "cooking": ["cook a meal together", "food tour", "recipe swap"],
    "hiking": ["hit the trails", "map a new route", "nature photography walk"],
    "travel": ["plan a weekend trip", "share travel stories", "language exchange"],
    "languages": ["language exchange", "conversation practice", "watch a foreign film"],
    "film": ["movie marathon", "film critique", "short film project"],
    "debate": ["debate session", "discuss current events", "mock trial"],
    "math": ["problem-solving session", "tutoring swap", "competition prep"],
    "science": ["lab visit", "paper discussion", "science fair project"],
    "entrepreneurship": ["pitch practice", "idea brainstorm", "networking coffee"],
    "design": ["critique each other's work", "design sprint", "UX walkthrough"],
    "meditation": ["meditate together", "mindfulness walk", "breathing exercise"],
    "dance": ["dance practice", "try a new style", "social dance event"],
    "sports": ["casual game", "training session", "watch a match together"],
    "basketball": ["pickup game", "shooting practice", "watch the NBA"],
    "football": ["pickup game", "training drill", "watch a match"],
    "soccer": ["pickup game", "training drill", "watch a match"],
    "tennis": ["rally practice", "singles match", "watch a tournament"],
    "climbing": ["climbing gym session", "outdoor route", "bouldering competition"],
}

# Fallback suggestions when no specific tag is found in the map.
_DEFAULT_ACTIVITIES: List[str] = ["grab a coffee", "chat and get to know each other"]


def suggest_activities(shared_interests: List[str]) -> List[str]:
    """
    Return a deduplicated list of suggested activities for a set of shared interest tags.

    For each shared tag we look up all associated activities, then union them.
    Unknown tags fall back to a generic set so the response is never empty.
    Time complexity: O(t * a) where t = number of shared tags, a = avg activities per tag.
    """
    if not shared_interests:
        return list(_DEFAULT_ACTIVITIES)

    activity_set: set[str] = set()
    found_any_tag = False

    for tag in shared_interests:
        tag_activities = INTEREST_ACTIVITIES.get(tag.lower())
        if tag_activities:
            activity_set.update(tag_activities)
            found_any_tag = True

    if not found_any_tag:
        return list(_DEFAULT_ACTIVITIES)

    # Return a stable, sorted list so the UI renders consistently.
    return sorted(activity_set)
