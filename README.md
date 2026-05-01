# Proximity Match

A location-based social matching app that connects nearby users who share interests, powered by Claude AI.

**Team:** Keshav, Neilay, Zavi — CBC x Anthropic x CDIS Hackathon

---

## What It Does

Proximity Match lets users check in at their current location and instantly discover other users nearby who share their interests. Claude AI generates personalized compatibility insights and suggests activities the two people could do together.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) + uvicorn |
| Database | SQLite (aiosqlite async) |
| Frontend | Single-page app (HTML/CSS/JS) with PWA support |
| AI | Anthropic Claude (`claude-opus-4-6`) |
| Deployment | Vercel (Python serverless) |

---

## Features

- **User registration & login** — PBKDF2-SHA256 password hashing, session token auth
- **Location check-in** — record latitude/longitude to become discoverable
- **Proximity matching** — Haversine distance + shared-interest scoring within a configurable radius
- **AI-powered insights** — Claude generates a personalized 2-sentence compatibility note for each match
- **Activity suggestions** — 50+ interest tags mapped to concrete things to do together
- **Match history** — persisted record of past matches with pagination
- **Real-time notifications** — WebSocket push when a new user checks in nearby
- **Rate limiting** — sliding-window per-IP limiter (returns `429` with `Retry-After`)
- **TTL cache** — match results cached for 30 s (configurable) to reduce DB load
- **PWA** — installable, offline shell, service worker

---

## Project Structure

```
CBC-Anthropic-x-CDIS-Hackaton/
├── api/
│   └── index.py              # Vercel serverless entry point
├── app/
│   ├── main.py               # FastAPI routes and app setup
│   ├── models.py             # Pydantic request/response schemas
│   ├── database.py           # SQLite schema, queries, and auth helpers
│   ├── matching.py           # Haversine distance and match scoring
│   ├── ai_matcher.py         # Claude API integration
│   ├── activity_suggester.py # Interest → activity mapping
│   ├── cache.py              # TTL LRU cache
│   └── rate_limiter.py       # Per-IP sliding-window rate limiter
├── static/
│   ├── index.html            # SPA frontend
│   ├── manifest.json         # PWA manifest
│   └── sw.js                 # Service worker
├── tests/                    # Full test suite (unit + integration)
├── .env.example              # Environment variable template
├── requirements.txt
└── vercel.json
```

---

## Getting Started

### Prerequisites

- Python 3.8+
- An [Anthropic API key](https://console.anthropic.com/)

### Installation

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd CBC-Anthropic-x-CDIS-Hackaton

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY and API_KEY_SALT at minimum
```

### Run Locally

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser.

### Run Tests

```bash
# All tests
python tests/run_all_tests.py

# Individual module
pytest tests/test_api_integration.py -v

# With coverage
pytest tests/ --cov=app
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Claude API key |
| `API_KEY_SALT` | `"default-dev-salt-change-me"` | Secret for hashing session tokens |
| `DATABASE_URL` | `./proximity_match.db` | SQLite database path |
| `INTEREST_WEIGHT` | `10.0` | Score multiplier per shared interest |
| `DISTANCE_WEIGHT` | `1.0` | Score penalty per km |
| `DEFAULT_RADIUS_KM` | `0.5` | Default search radius |
| `MAX_MATCHES_RETURNED` | `20` | Maximum matches per query |
| `MATCH_CACHE_TTL_SECONDS` | `30` | Match result cache duration |
| `RATE_LIMIT_MAX_REQUESTS` | `60` | Requests allowed per window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window duration |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:8000,...` | Comma-separated allowed origins |

---

## API Reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/register` | Create an account — returns `session_token` |
| `POST` | `/login` | Log in — returns `session_token` |
| `GET` | `/me` | Get current user profile |

All authenticated endpoints require the header: `X-Session-Token: <token>`

### Core Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/checkin` | Record location and become discoverable |
| `GET` | `/matches?radius_km=0.5` | Find nearby users with shared interests |
| `GET` | `/history?limit=50` | Retrieve past match history |
| `WS` | `/ws/{user_id}?session_token=TOKEN` | Real-time check-in notifications |

### Example: Register

```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice",
    "email": "alice@example.com",
    "password": "supersecret",
    "interests": ["hiking", "coding", "coffee"]
  }'
```

### Example: Find Matches

```bash
curl http://localhost:8000/matches?radius_km=1.0 \
  -H "X-Session-Token: <your-token>"
```

---

## Match Scoring

Each candidate is scored as:

```
score = (shared_interests_count × INTEREST_WEIGHT) − (distance_km × DISTANCE_WEIGHT)
```

Results are sorted by score descending. Claude then generates a short insight for each match in a single batched API call with prompt caching to minimize cost and latency.

---

## Deployment

The app is configured for Vercel's Python serverless runtime. `vercel.json` routes all traffic to `api/index.py`, which wraps the FastAPI app.

```bash
npm install -g vercel
vercel
```

> **Note:** SQLite on Vercel is ephemeral (stored in `/tmp`). Data does not persist across cold starts. For production persistence, migrate to PostgreSQL.

---

## Security Highlights

- Passwords hashed with PBKDF2-SHA256 (260,000 iterations, per-user 32-byte salt)
- Session tokens stored only as SHA-256 hashes; never logged
- Constant-time comparison to prevent timing attacks
- All inputs validated via Pydantic with strict bounds
- Rate limiting on every endpoint; `429` returned with `Retry-After`
- No secrets hardcoded — all configuration via environment variables
