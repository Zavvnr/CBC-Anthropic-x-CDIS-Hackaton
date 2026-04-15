"""
database.py — SQLite connection, schema, and query helpers.

Think of this module as the library card system: it controls how we open and
close the card catalogue (the database), sets up the shelves (tables) on
first run, and provides the only counters where borrowers (routes) can
interact with the catalogue — so every interaction is logged and safe.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)

_db_connection: Optional[aiosqlite.Connection] = None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    email           TEXT    NOT NULL UNIQUE,
    password_hash   TEXT    NOT NULL,
    password_salt   TEXT    NOT NULL,
    session_token_hash TEXT NOT NULL DEFAULT '',
    interests       TEXT    NOT NULL,
    is_active       INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS checkins (
    checkin_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(user_id),
    latitude      REAL    NOT NULL,
    longitude     REAL    NOT NULL,
    place_name    TEXT,
    checked_in_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS match_history (
    history_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id     INTEGER NOT NULL REFERENCES users(user_id),
    matched_user_id  INTEGER NOT NULL REFERENCES users(user_id),
    shared_interests TEXT    NOT NULL,
    distance_km      REAL    NOT NULL,
    score            REAL    NOT NULL,
    matched_at       TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email    ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active   ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_checkins_user  ON checkins(user_id);
CREATE INDEX IF NOT EXISTS idx_match_history_requester ON match_history(requester_id);
"""

# Migrations applied once against pre-existing databases (silently skipped if already present).
_MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN password_salt TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN session_token_hash TEXT NOT NULL DEFAULT ''",
]


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------

async def connect(database_url: str) -> None:
    """Open the SQLite connection and apply the schema."""
    global _db_connection
    _db_connection = await aiosqlite.connect(database_url)
    _db_connection.row_factory = aiosqlite.Row
    await _db_connection.executescript(_SCHEMA_SQL)
    await _run_migrations(_db_connection)
    await _db_connection.commit()
    logger.info("Database connected: %s", database_url)


async def _run_migrations(db: aiosqlite.Connection) -> None:
    """Apply additive ALTER TABLE migrations; skip silently if already applied."""
    for sql in _MIGRATIONS:
        try:
            await db.execute(sql)
        except Exception:
            pass  # column already exists
    await db.commit()


async def disconnect() -> None:
    """Close the SQLite connection gracefully."""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
        logger.info("Database disconnected.")


def get_connection() -> aiosqlite.Connection:
    """Return the live connection; raises if connect() was not called."""
    if _db_connection is None:
        raise RuntimeError("Database is not connected. Call connect() first.")
    return _db_connection


# ---------------------------------------------------------------------------
# Password hashing — PBKDF2-SHA256 with a per-user random salt
# ---------------------------------------------------------------------------

def _hash_password(password: str, salt_bytes: bytes) -> str:
    """Return a PBKDF2-SHA256 hex digest of the password using the given salt."""
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 260_000)
    return dk.hex()


def _hash_session_token(raw_token: str, app_salt: str) -> str:
    """Return a SHA-256 hex digest of the session token salted with the app-level salt."""
    return hashlib.sha256(f"{app_salt}:{raw_token}".encode()).hexdigest()


# ---------------------------------------------------------------------------
# User queries
# ---------------------------------------------------------------------------

async def create_user(
    name: str,
    email: str,
    password_plain: str,
    interests: List[str],
) -> int:
    """
    Insert a new user with a hashed password. Returns the new user_id.

    Raises aiosqlite.IntegrityError if the email is already registered.
    """
    salt_bytes = os.urandom(32)
    password_salt = salt_bytes.hex()
    password_hash = _hash_password(password_plain, salt_bytes)
    interests_json = json.dumps(interests)
    created_at = _utc_now_iso()
    db = get_connection()

    cursor = await db.execute(
        "INSERT INTO users "
        "(name, email, password_hash, password_salt, session_token_hash, interests, is_active, created_at) "
        "VALUES (?, ?, ?, ?, '', ?, 0, ?)",
        (name, email.lower().strip(), password_hash, password_salt, interests_json, created_at),
    )
    await db.commit()
    return cursor.lastrowid


async def create_session(user_id: int, app_salt: str) -> str:
    """
    Generate a new session token, store its hash, and return the raw token.

    Calling this again invalidates any previous session for the same user.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_session_token(raw_token, app_salt)
    db = get_connection()
    await db.execute(
        "UPDATE users SET session_token_hash = ? WHERE user_id = ?",
        (token_hash, user_id),
    )
    await db.commit()
    return raw_token


async def authenticate_by_credentials(
    email: str,
    password_plain: str,
) -> Optional[Dict[str, Any]]:
    """
    Verify email + password. Returns the user dict on success, None on failure.

    Passwords are never logged — only hashes are compared.
    """
    db = get_connection()
    async with db.execute(
        "SELECT user_id, name, interests, is_active, password_hash, password_salt "
        "FROM users WHERE email = ?",
        (email.lower().strip(),),
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        return None

    expected_hash = _hash_password(password_plain, bytes.fromhex(row["password_salt"]))
    # Use constant-time comparison to prevent timing attacks.
    if not secrets.compare_digest(expected_hash, row["password_hash"]):
        return None

    return {
        "user_id": row["user_id"],
        "name": row["name"],
        "interests": json.loads(row["interests"]),
        "is_active": bool(row["is_active"]),
    }


async def authenticate_by_session_token(
    raw_token: str,
    app_salt: str,
) -> Optional[Dict[str, Any]]:
    """
    Return the user row if the session token is valid, else None.

    Tokens are never logged — only hashes are compared.
    """
    token_hash = _hash_session_token(raw_token, app_salt)
    db = get_connection()

    async with db.execute(
        "SELECT user_id, name, interests, is_active "
        "FROM users WHERE session_token_hash = ?",
        (token_hash,),
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        return None

    return {
        "user_id": row["user_id"],
        "name": row["name"],
        "interests": json.loads(row["interests"]),
        "is_active": bool(row["is_active"]),
    }


# ---------------------------------------------------------------------------
# Check-in queries
# ---------------------------------------------------------------------------

async def upsert_checkin(
    user_id: int,
    latitude: float,
    longitude: float,
    place_name: Optional[str],
) -> str:
    """Record a check-in, mark the user active, and return the timestamp."""
    checked_in_at = _utc_now_iso()
    db = get_connection()

    await db.execute(
        "INSERT INTO checkins (user_id, latitude, longitude, place_name, checked_in_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, latitude, longitude, place_name, checked_in_at),
    )
    await db.execute("UPDATE users SET is_active = 1 WHERE user_id = ?", (user_id,))
    await db.commit()
    return checked_in_at


async def get_latest_checkin(user_id: int) -> Optional[Dict[str, Any]]:
    """Return the most recent check-in row for a user."""
    db = get_connection()
    async with db.execute(
        "SELECT latitude, longitude, place_name, checked_in_at "
        "FROM checkins WHERE user_id = ? ORDER BY checkin_id DESC LIMIT 1",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        return None

    return {
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "place_name": row["place_name"],
        "checked_in_at": row["checked_in_at"],
    }


async def get_active_users_with_location(excluding_user_id: int) -> List[Dict[str, Any]]:
    """Return all active users with their latest coordinates, excluding the requesting user."""
    db = get_connection()
    query = """
        SELECT u.user_id, u.name, u.interests,
               c.latitude, c.longitude, c.place_name
        FROM users u
        JOIN checkins c ON c.checkin_id = (
            SELECT MAX(ci.checkin_id) FROM checkins ci WHERE ci.user_id = u.user_id
        )
        WHERE u.is_active = 1 AND u.user_id != ?
    """
    async with db.execute(query, (excluding_user_id,)) as cursor:
        rows = await cursor.fetchall()

    return [
        {
            "user_id": row["user_id"],
            "name": row["name"],
            "interests": json.loads(row["interests"]),
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "place_name": row["place_name"],
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Match history queries
# ---------------------------------------------------------------------------

async def record_match_history(
    requester_id: int,
    matched_user_id: int,
    shared_interests: List[str],
    distance_km: float,
    score: float,
) -> None:
    """Persist a match event for history review."""
    db = get_connection()
    await db.execute(
        "INSERT INTO match_history "
        "(requester_id, matched_user_id, shared_interests, distance_km, score, matched_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (requester_id, matched_user_id, json.dumps(shared_interests), distance_km, score, _utc_now_iso()),
    )
    await db.commit()


async def get_match_history(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Return up to `limit` past matches for a user, newest first."""
    db = get_connection()
    query = """
        SELECT mh.history_id, mh.matched_user_id, u.name AS matched_user_name,
               mh.shared_interests, mh.distance_km, mh.score, mh.matched_at
        FROM match_history mh
        JOIN users u ON u.user_id = mh.matched_user_id
        WHERE mh.requester_id = ?
        ORDER BY mh.history_id DESC
        LIMIT ?
    """
    async with db.execute(query, (user_id, limit)) as cursor:
        rows = await cursor.fetchall()

    return [
        {
            "history_id": row["history_id"],
            "matched_user_id": row["matched_user_id"],
            "matched_user_name": row["matched_user_name"],
            "shared_interests": json.loads(row["shared_interests"]),
            "distance_km": row["distance_km"],
            "score": row["score"],
            "matched_at": row["matched_at"],
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()
