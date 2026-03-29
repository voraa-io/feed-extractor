"""Configuration and settings loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Supabase
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")

# Fetcher
FETCH_DELAY_SECONDS: float = float(os.environ.get("FETCH_DELAY_SECONDS", "2.0"))
FETCH_TIMEOUT_SECONDS: float = float(os.environ.get("FETCH_TIMEOUT_SECONDS", "30.0"))
USER_AGENT: str = (
    "Mozilla/5.0 (compatible; FeedExtractor/0.1; +https://github.com/voraa)"
)
