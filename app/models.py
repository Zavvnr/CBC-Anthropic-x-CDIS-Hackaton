"""
models.py — Pydantic request/response schemas for the proximity-match API.

Every field that enters the system from a client is validated here before
it touches any business logic or the database.
"""

from __future__ import annotations

import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_INTERESTS = 50
MAX_INTEREST_TAG_LENGTH = 40
MAX_NAME_LENGTH = 100
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0
MAX_RADIUS_KM = 50.0

_SAFE_TAG_PATTERN = re.compile(r"^[a-zA-Z0-9_\- ]+$")
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitise_tag(raw: str) -> str:
    """Lowercase and strip a single interest tag."""
    return raw.strip().lower()


# ---------------------------------------------------------------------------
# Auth models
# ---------------------------------------------------------------------------

class UserRegisterRequest(BaseModel):
    """Payload for creating a new user account."""

    name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=8, max_length=128)
    interests: List[str] = Field(..., min_length=1, max_length=MAX_INTERESTS)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        """Reject names that are only whitespace."""
        if not value.strip():
            raise ValueError("name must not be blank")
        return value.strip()

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        """Basic email format check — not exhaustive, just sanity."""
        cleaned = value.strip().lower()
        if not _EMAIL_PATTERN.match(cleaned):
            raise ValueError("invalid email address")
        return cleaned

    @field_validator("interests", mode="before")
    @classmethod
    def normalise_interests(cls, raw_tags: list) -> List[str]:
        """Lowercase, strip, deduplicate, and validate each interest tag."""
        cleaned: list[str] = []
        seen: set[str] = set()
        for tag in raw_tags:
            if not isinstance(tag, str):
                raise ValueError(f"Each interest must be a string, got: {type(tag)}")
            sanitised = _sanitise_tag(tag)
            if not sanitised:
                continue
            if len(sanitised) > MAX_INTEREST_TAG_LENGTH:
                raise ValueError(f"Interest tag too long: '{sanitised}'")
            if not _SAFE_TAG_PATTERN.match(sanitised):
                raise ValueError(f"Interest tag contains invalid characters: '{sanitised}'")
            if sanitised not in seen:
                seen.add(sanitised)
                cleaned.append(sanitised)
        if not cleaned:
            raise ValueError("At least one valid interest tag is required")
        return cleaned


class LoginRequest(BaseModel):
    """Payload for logging in with email + password."""

    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        return value.strip().lower()


class AuthResponse(BaseModel):
    """Returned after a successful register or login."""

    session_token: str
    user_id: int
    name: str
    interests: List[str]


class UserResponse(BaseModel):
    """Public user profile (session token is not included)."""

    user_id: int
    name: str
    interests: List[str]
    is_active: bool


# ---------------------------------------------------------------------------
# Check-in models
# ---------------------------------------------------------------------------

class CheckInRequest(BaseModel):
    """Payload for a user announcing their current location."""

    latitude: float = Field(..., ge=MIN_LATITUDE, le=MAX_LATITUDE)
    longitude: float = Field(..., ge=MIN_LONGITUDE, le=MAX_LONGITUDE)
    place_name: Optional[str] = Field(None, max_length=200)

    @field_validator("place_name")
    @classmethod
    def sanitise_place_name(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value else None


class CheckInResponse(BaseModel):
    """Confirmation returned after a successful check-in."""

    user_id: int
    latitude: float
    longitude: float
    place_name: Optional[str]
    checked_in_at: str


# ---------------------------------------------------------------------------
# Match models
# ---------------------------------------------------------------------------

class MatchedUserDetail(BaseModel):
    """A single match candidate with scoring details."""

    user_id: int
    name: str
    shared_interests: List[str]
    distance_km: float
    score: float
    suggested_activities: List[str]
    ai_insight: Optional[str] = None  # Claude-generated compatibility insight


class MatchQueryResponse(BaseModel):
    """Response envelope for GET /matches."""

    requesting_user_id: int
    radius_km: float
    matches: List[MatchedUserDetail]
    cached: bool = False


# ---------------------------------------------------------------------------
# Match history models
# ---------------------------------------------------------------------------

class MatchHistoryEntry(BaseModel):
    """One row from the match_history table."""

    history_id: int
    matched_user_id: int
    matched_user_name: str
    shared_interests: List[str]
    distance_km: float
    score: float
    matched_at: str


class MatchHistoryResponse(BaseModel):
    """Paginated match history for a user."""

    user_id: int
    history: List[MatchHistoryEntry]
