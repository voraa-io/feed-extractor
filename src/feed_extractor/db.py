"""Supabase client and database operations."""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from feed_extractor.config import SUPABASE_KEY, SUPABASE_URL


@lru_cache(maxsize=1)
def get_client() -> Client:
    """Return a cached Supabase client instance."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set. "
            "Copy .env.example to .env and fill in your credentials."
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def upsert_sources(sources: list[dict]) -> None:
    """Upsert source records into the sources table."""
    client = get_client()
    client.table("sources").upsert(sources, on_conflict="base_url").execute()


def insert_fetch_log(log: dict) -> None:
    """Insert a fetch log record."""
    client = get_client()
    client.table("fetch_logs").insert(log).execute()


def get_active_sources() -> list[dict]:
    """Return all active sources from the database."""
    client = get_client()
    result = client.table("sources").select("*").eq("active", True).execute()
    return result.data


def upsert_items(items: list[dict]) -> None:
    """Upsert canonical items into the items table."""
    if not items:
        return
    client = get_client()
    client.table("items").upsert(items, on_conflict="canonical_id").execute()


def get_places() -> list[dict]:
    """Return all San Pedro places for locality resolution."""
    client = get_client()
    result = client.table("san_pedro_places").select("*").execute()
    return result.data
