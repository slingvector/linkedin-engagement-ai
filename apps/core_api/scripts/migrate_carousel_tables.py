"""
Migration — Sprint 4 (Carousel Studio)
Adds: carousel_assets table, user_settings table.
Safe to run multiple times (uses IF NOT EXISTS).

Run from core_api root:
    python -m scripts.migrate_carousel_tables
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings

MIGRATION_SQL = """
-- ── carousel_assets table ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS carousel_assets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id             UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    slides_json         JSONB NOT NULL,
    pdf_url             TEXT,
    slide_count         INTEGER NOT NULL DEFAULT 7,
    status              VARCHAR(50) NOT NULL DEFAULT 'draft',
    linkedin_asset_urn  TEXT,
    brand_kit_snapshot  JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ,
    deleted_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_carousel_assets_post_id ON carousel_assets(post_id);

-- ── user_settings table ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_settings (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    primary_color    VARCHAR(7) DEFAULT '#0A66C2',
    logo_url         TEXT,
    font_family      VARCHAR(100) DEFAULT 'Inter',
    author_name      VARCHAR(200),
    author_tagline   VARCHAR(300),
    pillars          JSONB DEFAULT '[]',
    posts_per_week   INTEGER DEFAULT 3,
    preferred_formats JSONB DEFAULT '[]',
    auto_score_drafts BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ,
    deleted_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_user_settings_user_id ON user_settings(user_id);
"""


async def run():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=True)
    async with engine.begin() as conn:
        await conn.execute(text(MIGRATION_SQL))
    await engine.dispose()
    print("✅ Carousel Studio tables migration complete.")


if __name__ == "__main__":
    asyncio.run(run())
