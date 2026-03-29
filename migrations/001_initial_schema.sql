-- Feed Extractor V1: Initial schema for Supabase
-- Run this in the Supabase SQL Editor

-- Enable UUID generation
create extension if not exists "uuid-ossp";

-- ============================================================
-- Sources: curated list of sites to scrape
-- ============================================================
create table if not exists sources (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    base_url text not null unique,
    source_type text not null default 'website',
    fetch_method text not null default 'html',
    content_type text not null default 'mixed',
    trust_score real not null default 0.5,
    relevance_type text not null default 'exclusive_to_san_pedro',
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ============================================================
-- Fetch logs: raw fetch history for debugging
-- ============================================================
create table if not exists fetch_logs (
    id uuid primary key default uuid_generate_v4(),
    source_id uuid references sources(id) on delete cascade,
    url text not null,
    status_code int,
    content_hash text,
    fetched_at timestamptz not null default now(),
    raw_content text
);

create index if not exists idx_fetch_logs_source_id on fetch_logs(source_id);
create index if not exists idx_fetch_logs_fetched_at on fetch_logs(fetched_at desc);

-- ============================================================
-- Items: canonical feed items
-- ============================================================
create table if not exists items (
    id uuid primary key default uuid_generate_v4(),
    canonical_id text not null unique,
    item_type text not null default 'event',
    title text not null,
    summary text,
    business_name text,
    venue_name text,
    address_text text,
    municipality text default 'San Pedro Garza García',
    is_san_pedro boolean not null default true,
    location_confidence real not null default 0.0,
    matched_place text,
    start_datetime timestamptz,
    end_datetime timestamptz,
    valid_until timestamptz,
    price_text text,
    discount_text text,
    terms_text text,
    image_url text,
    source_urls text[] not null default '{}',
    source_names text[] not null default '{}',
    source_count int not null default 1,
    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    status text not null default 'unknown',
    quality_score real not null default 0.0,
    raw_extracted jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_items_status on items(status);
create index if not exists idx_items_quality_score on items(quality_score desc);
create index if not exists idx_items_is_san_pedro on items(is_san_pedro);
create index if not exists idx_items_item_type on items(item_type);

-- ============================================================
-- San Pedro places: lookup table for locality resolution
-- ============================================================
create table if not exists san_pedro_places (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    place_type text not null,
    address text,
    aliases text[] not null default '{}',
    lat real,
    lng real
);

-- ============================================================
-- Auto-update updated_at on sources and items
-- ============================================================
create or replace function update_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger sources_updated_at
    before update on sources
    for each row execute function update_updated_at();

create trigger items_updated_at
    before update on items
    for each row execute function update_updated_at();
