"""
main.py — FastAPI application entry point: routes, startup/shutdown, and static file serving.

Think of this file as the front desk of a hotel: it greets every incoming
request, checks credentials, directs the guest to the right department
(matching, check-in, history), and makes sure no one floods the lobby
(rate limiting) or sneaks in through the back (auth guards).
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, List, Optional

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import database, matching, activity_suggester, ai_matcher, cache, rate_limiter
from app.cache import MISSING, match_cache
from app.models import (
    AuthResponse,
    CheckInRequest,
    CheckInResponse,
    LoginRequest,
    MatchHistoryResponse,
    MatchQueryResponse,
    MatchedUserDetail,
    MatchHistoryEntry,
    UserRegisterRequest,
    UserResponse,
)
from app.matching import MatchConfig, UserLocation, find_matches
from app.rate_limiter import enforce_rate_limit, configure_limiter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------

# On Vercel the filesystem is ephemeral; /tmp is writable per cold-start instance.
_default_db = "/tmp/proximity_match.db" if os.getenv("VERCEL") else "./proximity_match.db"
DATABASE_URL = os.getenv("DATABASE_URL", _default_db)
API_KEY_SALT = os.getenv("API_KEY_SALT", "default-dev-salt-change-me")
INTEREST_WEIGHT = float(os.getenv("INTEREST_WEIGHT", "10.0"))
DISTANCE_WEIGHT = float(os.getenv("DISTANCE_WEIGHT", "1.0"))
DEFAULT_RADIUS_KM = float(os.getenv("DEFAULT_RADIUS_KM", "0.5"))
MAX_MATCHES_RETURNED = int(os.getenv("MAX_MATCHES_RETURNED", "20"))
MATCH_CACHE_TTL_SECONDS = float(os.getenv("MATCH_CACHE_TTL_SECONDS", "30.0"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60"))
RATE_LIMIT_WINDOW_SECONDS = float(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60.0"))

_CORS_ORIGINS_RAW = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000",
)
CORS_ALLOWED_ORIGINS: List[str] = [o.strip() for o in _CORS_ORIGINS_RAW.split(",") if o.strip()]


# ---------------------------------------------------------------------------
# Application lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to the database on startup; close it on shutdown."""
    # Apply env-var config to singletons before serving any requests.
    configure_limiter(
        max_requests=RATE_LIMIT_MAX_REQUESTS,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )
    # Reconfigure cache TTL; max_size stays at module default (512).
    cache.match_cache._ttl_seconds = MATCH_CACHE_TTL_SECONDS

    await database.connect(DATABASE_URL)
    logger.info("Application startup complete.")
    yield
    await database.disconnect()
    logger.info("Application shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Proximity Match",
    description="Connect people who share interests and are physically nearby.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Session-Token"],
)


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

async def require_auth(request: Request) -> dict:
    """
    FastAPI dependency: extract and validate the X-Session-Token header.

    Returns the authenticated user dict. Raises 401 if the token is missing
    or invalid. Tokens are never written to logs.
    """
    raw_token = request.headers.get("X-Session-Token")
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Session-Token header.",
        )

    user = await database.authenticate_by_session_token(raw_token, API_KEY_SALT)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
        )
    return user


# ---------------------------------------------------------------------------
# Static file serving
# ---------------------------------------------------------------------------

STATIC_DIR = Path(__file__).parent.parent / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False, dependencies=[Depends(enforce_rate_limit)])
async def serve_index():
    """Serve the single-page frontend."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/manifest.json", include_in_schema=False)
async def serve_manifest():
    """Serve the PWA manifest (needed at the root for iOS Add to Home Screen)."""
    return FileResponse(str(STATIC_DIR / "manifest.json"), media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
async def serve_sw():
    """Serve the service worker at the root scope."""
    return FileResponse(
        str(STATIC_DIR / "sw.js"),
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )


# ---------------------------------------------------------------------------
# Routes: User registration
# ---------------------------------------------------------------------------

@app.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account with email and password.",
    dependencies=[Depends(enforce_rate_limit)],
)
async def register_user(payload: UserRegisterRequest) -> AuthResponse:
    """
    Create a new user. Returns a session token immediately so the client is
    logged in right after registration without a separate login call.
    """
    try:
        user_id = await database.create_user(
            name=payload.name,
            email=payload.email,
            password_plain=payload.password,
            interests=payload.interests,
        )
    except Exception as exc:
        if "UNIQUE constraint failed: users.email" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
        raise

    session_token = await database.create_session(user_id, API_KEY_SALT)
    return AuthResponse(
        session_token=session_token,
        user_id=user_id,
        name=payload.name,
        interests=payload.interests,
    )


@app.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in with email and password.",
    dependencies=[Depends(enforce_rate_limit)],
)
async def login_user(payload: LoginRequest) -> AuthResponse:
    """Verify credentials and issue a new session token."""
    user = await database.authenticate_by_credentials(payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    session_token = await database.create_session(user["user_id"], API_KEY_SALT)
    return AuthResponse(
        session_token=session_token,
        user_id=user["user_id"],
        name=user["name"],
        interests=user["interests"],
    )


@app.get(
    "/me",
    response_model=UserResponse,
    summary="Return the authenticated user's profile.",
    dependencies=[Depends(enforce_rate_limit)],
)
async def get_my_profile(current_user: Annotated[dict, Depends(require_auth)]) -> UserResponse:
    """Fetch the caller's own profile."""
    return UserResponse(**current_user)


# ---------------------------------------------------------------------------
# Routes: Check-in
# ---------------------------------------------------------------------------

@app.post(
    "/checkin",
    response_model=CheckInResponse,
    summary="Record the user's current location and mark them active.",
    dependencies=[Depends(enforce_rate_limit)],
)
async def check_in(
    payload: CheckInRequest,
    current_user: Annotated[dict, Depends(require_auth)],
) -> CheckInResponse:
    """
    Store the user's location and activate their profile for matching.
    Invalidates the match cache for this user so stale results are not served.
    """
    user_id = current_user["user_id"]
    checked_in_at = await database.upsert_checkin(
        user_id=user_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        place_name=payload.place_name,
    )

    # Bust cache entries keyed on this user so fresh results are returned.
    for radius in [DEFAULT_RADIUS_KM, 0.1, 0.25, 1.0, 2.0, 5.0]:
        match_cache.invalidate((user_id, radius))

    return CheckInResponse(
        user_id=user_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        place_name=payload.place_name,
        checked_in_at=checked_in_at,
    )


# ---------------------------------------------------------------------------
# Routes: Matching
# ---------------------------------------------------------------------------

@app.get(
    "/matches",
    response_model=MatchQueryResponse,
    summary="Find active nearby users who share interests with the caller.",
    dependencies=[Depends(enforce_rate_limit)],
)
async def get_matches(
    current_user: Annotated[dict, Depends(require_auth)],
    radius_km: float = DEFAULT_RADIUS_KM,
) -> MatchQueryResponse:
    """
    Run the matching engine and return ranked candidates.

    Results are cached per (user_id, radius_km) for MATCH_CACHE_TTL_SECONDS seconds
    to avoid hammering the DB on repeated polls.
    """
    if radius_km <= 0 or radius_km > 50.0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="radius_km must be between 0 (exclusive) and 50.",
        )

    user_id = current_user["user_id"]
    cache_key = (user_id, round(radius_km, 3))

    # Attempt to serve from cache.
    cached_result = match_cache.get(cache_key)
    if cached_result is not MISSING:
        cached_result["cached"] = True
        return MatchQueryResponse(**cached_result)

    # Check that the user has checked in.
    checkin = await database.get_latest_checkin(user_id)
    if checkin is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must check in before searching for matches.",
        )

    target = UserLocation(
        user_id=user_id,
        name=current_user["name"],
        interests=current_user["interests"],
        latitude=checkin["latitude"],
        longitude=checkin["longitude"],
    )

    active_rows = await database.get_active_users_with_location(excluding_user_id=user_id)
    candidates = [
        UserLocation(
            user_id=row["user_id"],
            name=row["name"],
            interests=row["interests"],
            latitude=row["latitude"],
            longitude=row["longitude"],
        )
        for row in active_rows
    ]

    config = MatchConfig(
        max_radius_km=radius_km,
        interest_weight=INTEREST_WEIGHT,
        distance_weight=DISTANCE_WEIGHT,
        top_n=MAX_MATCHES_RETURNED,
    )
    raw_matches = find_matches(target, candidates, config)

    # Single Claude call for all matches — returns {user_id: insight_text}.
    ai_insights = await ai_matcher.generate_match_insights(
        user_name=current_user["name"],
        user_interests=current_user["interests"],
        matches=[
            {
                "user_id": m.user_id,
                "name": m.name,
                "shared_interests": m.shared_interests,
                "distance_km": m.distance_km,
            }
            for m in raw_matches
        ],
    )

    match_details: List[MatchedUserDetail] = []
    for match in raw_matches:
        activities = activity_suggester.suggest_activities(match.shared_interests)
        detail = MatchedUserDetail(
            user_id=match.user_id,
            name=match.name,
            shared_interests=match.shared_interests,
            distance_km=match.distance_km,
            score=match.score,
            suggested_activities=activities,
            ai_insight=ai_insights.get(match.user_id),
        )
        match_details.append(detail)

        # Persist the match event for history.
        await database.record_match_history(
            requester_id=user_id,
            matched_user_id=match.user_id,
            shared_interests=match.shared_interests,
            distance_km=match.distance_km,
            score=match.score,
        )

    response_payload = {
        "requesting_user_id": user_id,
        "radius_km": radius_km,
        "matches": [m.model_dump() for m in match_details],
        "cached": False,
    }
    match_cache.set(cache_key, response_payload)

    return MatchQueryResponse(
        requesting_user_id=user_id,
        radius_km=radius_km,
        matches=match_details,
        cached=False,
    )


# ---------------------------------------------------------------------------
# Routes: Match history
# ---------------------------------------------------------------------------

@app.get(
    "/history",
    response_model=MatchHistoryResponse,
    summary="Return the authenticated user's past match history.",
    dependencies=[Depends(enforce_rate_limit)],
)
async def get_history(
    current_user: Annotated[dict, Depends(require_auth)],
    limit: int = 50,
) -> MatchHistoryResponse:
    """Fetch up to `limit` past matches, newest first."""
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="limit must be between 1 and 200.",
        )

    user_id = current_user["user_id"]
    rows = await database.get_match_history(user_id, limit=limit)

    history_entries = [
        MatchHistoryEntry(
            history_id=row["history_id"],
            matched_user_id=row["matched_user_id"],
            matched_user_name=row["matched_user_name"],
            shared_interests=row["shared_interests"],
            distance_km=row["distance_km"],
            score=row["score"],
            matched_at=row["matched_at"],
        )
        for row in rows
    ]

    return MatchHistoryResponse(user_id=user_id, history=history_entries)


# ---------------------------------------------------------------------------
# WebSocket: real-time match push
# ---------------------------------------------------------------------------

# Simple in-memory registry of connected sockets — keyed by user_id.
# In a multi-process deployment, replace with a Redis pub/sub fan-out.
_active_websockets: dict[int, WebSocket] = {}


@app.websocket("/ws/{user_id}")
async def websocket_match_push(websocket: WebSocket, user_id: int):
    """
    WebSocket endpoint for real-time match notifications.

    The client connects here; when a POST /checkin is processed for any user,
    connected sockets receive a lightweight ping so they can refresh matches.
    Note: API key auth over WebSocket uses a query param for simplicity.
    """
    raw_token = websocket.query_params.get("session_token")
    if not raw_token:
        await websocket.close(code=1008)  # 1008 = Policy Violation
        return

    user = await database.authenticate_by_session_token(raw_token, API_KEY_SALT)
    if user is None or user["user_id"] != user_id:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    _active_websockets[user_id] = websocket
    logger.info("WebSocket connected: user_id=%d", user_id)

    try:
        while True:
            # Keep the connection alive; client sends pings to prevent timeout.
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: user_id=%d", user_id)
    finally:
        _active_websockets.pop(user_id, None)


async def _broadcast_checkin_event(checked_in_user_id: int) -> None:
    """Notify all connected WebSocket clients that someone new has checked in."""
    message = json.dumps({"event": "new_checkin", "user_id": checked_in_user_id})
    disconnected_ids = []
    for uid, ws in _active_websockets.items():
        try:
            await ws.send_text(message)
        except Exception:
            disconnected_ids.append(uid)
    for uid in disconnected_ids:
        _active_websockets.pop(uid, None)
