"""CLI entry point for the feed extractor."""

from __future__ import annotations

import logging
import sys

import click

from feed_extractor.pipeline import run_pipeline


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def cli(verbose: bool) -> None:
    """San Pedro Garza García feed extractor pipeline."""
    _setup_logging(verbose)


@cli.command()
@click.option("--skip-db", is_flag=True, help="Skip Supabase operations")
def run(skip_db: bool) -> None:
    """Run the full extraction pipeline."""
    items = run_pipeline(skip_db=skip_db)
    click.echo(f"\nDone. {len(items)} items in feed.")


@cli.command()
def fetch() -> None:
    """Fetch all sources without extracting."""
    from feed_extractor.modules.fetcher import fetch_all_sources
    from feed_extractor.modules.sources import load_sources_from_file

    sources = load_sources_from_file()
    results = fetch_all_sources(sources)
    ok = sum(1 for r in results if r.ok)
    click.echo(f"Fetched {ok}/{len(results)} sources successfully.")
    for r in results:
        status = "OK" if r.ok else f"FAIL ({r.error or r.status_code})"
        click.echo(f"  {r.source.name}: {status}")


@cli.command()
def sources() -> None:
    """List all configured sources."""
    from feed_extractor.modules.sources import load_sources_from_file

    sources_list = load_sources_from_file()
    click.echo(f"Sources ({len(sources_list)}):\n")
    for s in sources_list:
        click.echo(f"  [{s.relevance_type}] {s.name}")
        click.echo(f"    {s.base_url}")
        click.echo(f"    type={s.source_type} method={s.fetch_method} trust={s.trust_score}")
        click.echo()


@cli.command()
def stats() -> None:
    """Show item counts from Supabase."""
    from feed_extractor.db import get_client

    client = get_client()

    total = client.table("items").select("id", count="exact").execute()
    active = client.table("items").select("id", count="exact").eq("status", "active").execute()
    upcoming = client.table("items").select("id", count="exact").eq("status", "upcoming").execute()

    click.echo("Feed stats:")
    click.echo(f"  Total items:    {total.count}")
    click.echo(f"  Active:         {active.count}")
    click.echo(f"  Upcoming:       {upcoming.count}")


if __name__ == "__main__":
    cli()
