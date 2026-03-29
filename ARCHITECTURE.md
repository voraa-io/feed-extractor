# Architecture Decisions

## Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Natural fit for scraping, data pipelines |
| Package manager | Poetry | Project standard |
| Database | Supabase (PostgreSQL) | Hosted, managed, existing team familiarity |
| HTTP client | httpx | Async-capable, modern |
| HTML parsing | BeautifulSoup + lxml | Robust, well-documented |
| CLI framework | Click | Simple, composable commands |
| Date parsing | python-dateutil | Handles fuzzy/Spanish dates |
| Hosting | Local / VPS + cron | Simple for V1, no over-engineering |

## Design Principles

- **Rules first, no LLMs** — all extraction, filtering, and scoring is deterministic for V1
- **San Pedro only** — strict geographic scope before expanding
- **Curated sources** — hand-picked, no autonomous discovery
- **Skip RLS** — internal pipeline, no multi-tenant access needed yet

## Pipeline Flow

```
Sources (JSON) → Fetch (httpx) → Extract (BS4) → Location filter → Time filter → Dedup → Score → Supabase + JSON/MD output
```

## Database

- Hosted on Supabase (project: xqsxyngczqlydbpzjfay)
- 4 tables: sources, fetch_logs, items, san_pedro_places
- Schema in `migrations/001_initial_schema.sql`
