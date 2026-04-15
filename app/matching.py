"""
matching.py — Haversine distance calculation and interest-proximity matching engine.

Analogy: think of each user as a lighthouse. The matching engine looks at every
other lighthouse currently lit (active), measures how far away it is, counts
how many signals (interests) both lighthouses share, and ranks them by a
combined "worthiness" score — closer and more overlap = higher rank.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Constants — defaults; callers should inject via MatchConfig instead of
# relying on these directly so the engine stays stateless and testable.
# ---------------------------------------------------------------------------

EARTH_RADIUS_KM = 6371.0
DEFAULT_INTEREST_WEIGHT = 10.0
DEFAULT_DISTANCE_WEIGHT = 1.0
DEFAULT_MAX_RADIUS_KM = 0.5
DEFAULT_TOP_N = 20


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class UserLocation:
    """Minimal user record needed by the matching engine."""

    user_id: int
    name: str
    interests: List[str]   # already lowercased and deduplicated
    latitude: float
    longitude: float


@dataclass
class MatchResult:
    """One ranked match candidate produced by the engine."""

    user_id: int
    name: str
    shared_interests: List[str]
    distance_km: float
    score: float


@dataclass
class MatchConfig:
    """
    Injectable configuration for the matching engine.

    Separating config from the algorithm keeps the engine stateless and
    easy to unit-test with arbitrary parameters.
    """

    max_radius_km: float = DEFAULT_MAX_RADIUS_KM
    interest_weight: float = DEFAULT_INTEREST_WEIGHT
    distance_weight: float = DEFAULT_DISTANCE_WEIGHT
    top_n: int = DEFAULT_TOP_N


# ---------------------------------------------------------------------------
# Haversine formula
# ---------------------------------------------------------------------------

def haversine_distance_km(
    lat1_deg: float,
    lng1_deg: float,
    lat2_deg: float,
    lng2_deg: float,
) -> float:
    """
    Return the great-circle distance in kilometres between two (lat, lng) points.

    Uses the Haversine formula — accurate to within ~0.3% for distances < 1000 km,
    which is more than sufficient for the sub-500m proximity use-case here.
    Time complexity: O(1) — pure arithmetic, no loops.
    """
    lat1 = math.radians(lat1_deg)
    lat2 = math.radians(lat2_deg)
    delta_lat = math.radians(lat2_deg - lat1_deg)
    delta_lng = math.radians(lng2_deg - lng1_deg)

    # Haversine intermediate value.
    haversine_angle = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
    )
    central_angle = 2 * math.asin(math.sqrt(haversine_angle))
    return EARTH_RADIUS_KM * central_angle


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def compute_match_score(
    interest_overlap: int,
    distance_km: float,
    config: MatchConfig,
) -> float:
    """
    Compute a match quality score — higher is better.

    score = interest_overlap * INTEREST_WEIGHT - distance_km * DISTANCE_WEIGHT

    More shared interests and shorter distance both improve the score.
    The subtraction means score can go negative for very distant users —
    callers should still respect the radius filter as the primary gate.
    """
    return interest_overlap * config.interest_weight - distance_km * config.distance_weight


# ---------------------------------------------------------------------------
# Matching engine
# ---------------------------------------------------------------------------

def find_matches(
    target_user: UserLocation,
    candidate_users: List[UserLocation],
    config: Optional[MatchConfig] = None,
) -> List[MatchResult]:
    """
    Find and rank users who share interests with target_user and are within radius.

    Algorithm: O(n) scan over candidate_users with O(k) set intersection per candidate
    where k = avg number of interests. Total: O(n * k), which is effectively O(n)
    for realistic interest-list sizes.

    Returns at most config.top_n results, sorted by score descending.
    """
    if config is None:
        config = MatchConfig()

    target_interest_set = set(target_user.interests)
    scored_candidates: List[MatchResult] = []

    for candidate in candidate_users:
        if candidate.user_id == target_user.user_id:
            continue  # never match a user with themselves

        distance_km = haversine_distance_km(
            target_user.latitude,
            target_user.longitude,
            candidate.latitude,
            candidate.longitude,
        )

        if distance_km > config.max_radius_km:
            continue  # outside search radius — skip early

        shared_interests = sorted(
            target_interest_set.intersection(candidate.interests)
        )

        if not shared_interests:
            continue  # no overlap — not a valid match

        score = compute_match_score(len(shared_interests), distance_km, config)
        scored_candidates.append(
            MatchResult(
                user_id=candidate.user_id,
                name=candidate.name,
                shared_interests=shared_interests,
                distance_km=round(distance_km, 4),
                score=round(score, 4),
            )
        )

    # Sort descending by score; secondary sort by name for stable ordering.
    scored_candidates.sort(key=lambda m: (-m.score, m.name))
    return scored_candidates[: config.top_n]
