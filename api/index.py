"""
api/index.py — Vercel Python serverless entry point.

Vercel's @vercel/python runtime discovers this file and serves the ASGI app.
The database is stored in /tmp (writable on Vercel, ephemeral per cold start).
"""

import sys
import os

# Add the project root to the Python path so `app.*` imports resolve correctly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402

# Vercel expects the ASGI handler to be named `handler` or `app`.
handler = app
