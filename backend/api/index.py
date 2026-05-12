"""
backend/api/index.py
─────────────────────
Vercel serverless entry point.
Vercel looks for a file at api/index.py and calls the `app` or `handler` object.
We import our FastAPI app and Vercel's ASGI adapter handles the rest.
"""

import sys
import os

# Make sure our app module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app  # noqa: F401 — Vercel picks up `app` automatically
