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

### Eventbrite data structure

Events are in a `<script>` tag as `window.__SERVER_DATA__` JSON. Each event has:
- `name` — event title
- `start_date`, `end_date` — dates
- `description` — event description
- `image` — cover image with multiple sizes
- `url` — link to event detail page
- `location.address` — full address (street, city, postal code, country)
- `location.geo` — lat/lng coordinates

Also available in `<script type="application/ld+json">` as schema.org structured data.

### Next steps

- Write an Eventbrite extractor (structured JSON, high quality)
- Check Pangea's /eventos page and Sonora's /especiales/ pages
- Consider other aggregators or discovery approaches for sources that don't have web-published events
