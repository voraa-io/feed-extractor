# Phase 2: Learnings

## Source inspection results (2026-03-28)

We inspected all 7 working sources. Only 1 has actual F&B event data.

### What we found

| Source | URL | What's actually on the page | Has events? |
|--------|-----|----------------------------|-------------|
| Grupo Pangea | grupopangea.com | Corporate homepage, lists their restaurant brands | No |
| Pangea Restaurante | pangearestaurante.com | Restaurant homepage (hero, about, reservations). Has a nav link to /eventos (different URL, not scraped) | No (but /eventos page exists) |
| Colmillo | colmillo.mx | Restaurant homepage. Menu, locations, OpenTable reservations. 3 locations listed (Artz Pedregal, Masaryk Polanco, Arboleda Monterrey) | No |
| Sonora Grill | sonoragrill.com.mx/promociones | Promo terms & conditions page. 7 standing promos (wine deals, kids eat free, etc). Has a carousel linking to /especiales/ pages | Weak — promos not events |
| Arboleda | arboleda.mx | Real estate development marketing page (Next.js + Prismic CMS). Mentions "gastronomía" as an amenity, zero actual events | No |
| Maverick | maverick.com.mx | **Wrong site entirely** — this is a creative agency (branding, marketing), not a bar or nightlife venue | No |
| **Eventbrite SP F&B** | eventbrite.com/d/mexico--san-pedro.../food--and--drink/ | **Real event listings.** Structured JSON data in `window.__SERVER_DATA__` with title, dates, venue, description, price, location, images | **Yes** |

### Key takeaway

Most restaurant/venue websites in San Pedro **do not publish events on their main pages**. They use their sites for:
- Brand/about info
- Menus
- Reservations (OpenTable, CoverManager)
- Location info

Events, when they exist, tend to be on:
- **Aggregators** (Eventbrite, AllEvents)
- **Social media** (Instagram stories — not scrapable)
- **Separate subpages** (like Pangea's /eventos or Sonora's /especiales/)
- **Nowhere** (announced via WhatsApp, word of mouth)

### What this means for the pipeline

1. **Aggregators are the best V1 source** — Eventbrite has structured data with everything we need
2. **Restaurant homepages are mostly useless** for event discovery — they're static marketing pages
3. **Subpages might work** — some sites have /eventos or /especiales/ pages worth checking
4. **The "curated source list of venue websites" approach has limits** — unless a venue actively publishes events on their website, there's nothing to scrape

---

## Eventbrite extractor results (2026-03-29)

### What worked

- Eventbrite embeds structured JSON in `window.__SERVER_DATA__` — we parse that directly
- Also has JSON-LD (`<script type="application/ld+json">`) as a fallback
- Each event has: name, start/end date+time, venue, address, description, image, tags, tickets URL, timezone
- Extractor produces clean CandidateItems with all fields populated

### Eventbrite data structure

Events are in `window.__SERVER_DATA__.search_data.events.results[]`. Each event has:
- `name` — event title
- `start_date`, `end_date`, `start_time`, `end_time` — dates
- `summary` — short description
- `image.image_sizes.large/medium/small` — cover images
- `url` — link to event detail page
- `primary_venue.name` — venue name
- `primary_venue.address` — full address (street, city, region, postal code, lat/lng)
- `tags[]` — category tags (Food & Drink, etc.)
- `tickets_url` — direct checkout link
- `timezone` — America/Monterrey

### Generic extractor produces garbage on restaurant homepages

When the generic extractor runs on sites like Grupo Pangea, Colmillo, etc., it pulls:
- Section headings as "events" (HISTORIA, FACTURACIÓN ELECTRÓNICA)
- Phone numbers, footer text, job postings
- CoverManager reservation widgets
- SEO boilerplate

**Fix:** Added `SKIP_GENERIC` set in extractor.py — sources without a custom extractor and no known event structure get skipped entirely. No more garbage.

### Location filter caught a real issue

Eventbrite was initially marked as `exclusive_to_san_pedro`, which gave all its events a baseline confidence boost (0.65) even without location evidence. But Eventbrite returns events from the broader Monterrey area, not just San Pedro.

- "Rosas de chocolate" — address is Tiburcio Colunga 932, Monterrey (CP 64104) — NOT San Pedro
- "Sculpting Nights" — address is Gral. Porfirio Díaz 223, San Pedro Garza García (CP 66200) — IS San Pedro

**Fix:** Changed Eventbrite's `relevance_type` from `exclusive_to_san_pedro` to `regional`. Now only events with explicit San Pedro location evidence pass the filter. "Rosas de chocolate" correctly dropped.

### Current pipeline output

After all fixes, a clean run produces:
- 7 sources fetched (all 200 OK)
- 6 skipped (no event content), 1 extracted (Eventbrite)
- 2 candidates from Eventbrite
- 1 dropped by location filter (not in San Pedro)
- **1 real event in the final feed** with score 0.655

### The bottleneck is source quantity, not pipeline quality

The pipeline works correctly — it fetches, extracts structured data, filters by location, scores, and outputs clean results. The problem is that only 1 source produces data, and Eventbrite only has ~2 F&B events for San Pedro at any given time.

### Unexplored leads

- **Pangea /eventos page** — nav link exists at `pangearestaurante.com/carta-pangea-copy-copy/` — not yet fetched
- **Sonora Grill /especiales/** — carousel links to posada and fin2026 special event pages — not yet fetched
- **More Eventbrite queries** — broader categories, different search terms, nearby areas
- **Other aggregators** — AllEvents returned 403 (bot block), Meetup not yet tried
