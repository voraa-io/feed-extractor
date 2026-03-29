# Phase 2: Fetch + Extract (F&B Events)

## Status: IN PROGRESS

## Goal

For each working source, answer these questions:

1. **Does the page contain F&B events at all?** (tastings, dinners, themed nights, etc.)
2. **Where in the HTML are they?** (CSS selectors, structure)
3. **What fields can we extract?** (title, date, description, price, venue)
4. **Is it static HTML or JS-rendered?** (do we need a browser?)
5. **How often does the content change?** (daily, weekly, monthly)
6. **Is it a list of events or a single-page with mixed content?**

## What we're looking for per event

- Event name / title
- Date and time (or date range)
- Venue / restaurant name
- Event type (tasting, dinner, brunch, themed night, etc.)
- Price if available
- Description / details
- Image URL
- Link to event detail page

## Source inspection status

| Source | Has events? | Structure known? | Extractor written? |
|--------|-------------|------------------|-------------------|
| Grupo Pangea | ? | ? | No |
| Pangea Restaurante | ? | ? | No |
| Colmillo | ? | ? | No |
| Sonora Grill | ? | ? | No |
| Arboleda San Pedro | ? | ? | No |
| Maverick | ? | ? | No |
| Eventbrite SP F&B | ? | ? | No |

## Tasks

- [ ] Remove dead sources from sources.json
- [ ] Inspect HTML from each working source (answer the 6 questions above)
- [ ] Write per-source extractors for sources that have events
- [ ] Test end-to-end with real event data
- [ ] Verify items land in Supabase correctly

## Dead sources (removed)

Bardot, Ryoshi, Fashion Drive, Plaza Auriga (DNS fail), Strana, Mochomos (SSL errors), Grupo Costeño, AllEvents (403 blocked), Arboleda /eventos (404)
