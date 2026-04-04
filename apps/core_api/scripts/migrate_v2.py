"""
V2 Schema Migration — Add V2 columns + new tables to existing DB.

This is a non-destructive additive migration that:
  1. Adds V2 columns to the `posts` table (virality_score, score_breakdown,
     hook_alternatives, score_updated_at)
  2. Creates the `carousel_assets` table
  3. Creates the `user_settings` table

Safe to run multiple times — uses IF NOT EXISTS / IF NOT EXISTS syntax.
Does NOT drop or alter existing data.
"""

import asyncio
import structlog
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection
from sqlalchemy import text

from app.config import get_settings

logger = structlog.get_logger()


# ── SQL statements — all idempotent ──────────────────────────────────────────

V2_MIGRATIONS = [
    # Sprint 3 — Virality columns on posts
    """
    ALTER TABLE posts
        ADD COLUMN IF NOT EXISTS virality_score INTEGER,
        ADD COLUMN IF NOT EXISTS score_breakdown JSONB,
        ADD COLUMN IF NOT EXISTS hook_alternatives JSONB,
        ADD COLUMN IF NOT EXISTS actual_engagement_rate FLOAT,
        ADD COLUMN IF NOT EXISTS score_updated_at TIMESTAMPTZ
    ;
    """,

    # Sprint 4 — carousel_assets table
    """
    CREATE TABLE IF NOT EXISTS carousel_assets (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        status VARCHAR(32) NOT NULL DEFAULT 'draft',
        slides_json JSONB NOT NULL DEFAULT '[]',
        pdf_url TEXT,
        linkedin_asset_urn TEXT,
        brand_kit_snapshot JSONB,
        slide_count INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        deleted_at TIMESTAMPTZ
    );
    """,

    # Sprint 4 — user_settings table (brand kit + posting preferences)
    # Matches ORM: UserSettings(Base, UUIDMixin, TimestampMixin)
    # UUIDMixin → id UUID PK; TimestampMixin → created_at, updated_at, deleted_at
    """
    CREATE TABLE IF NOT EXISTS user_settings (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        primary_color VARCHAR(7) DEFAULT '#0A66C2',
        logo_url TEXT,
        font_family VARCHAR(100) DEFAULT 'Inter',
        author_name VARCHAR(200),
        author_tagline VARCHAR(300),
        pillars JSONB DEFAULT '[]',
        posts_per_week INTEGER DEFAULT 3,
        preferred_formats JSONB DEFAULT '[]',
        auto_score_drafts BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        deleted_at TIMESTAMPTZ
    );
    """,

    # Add missing columns to user_settings if table already existed without them
    """
    ALTER TABLE user_settings
        ADD COLUMN IF NOT EXISTS pillars JSONB DEFAULT '[]',
        ADD COLUMN IF NOT EXISTS posts_per_week INTEGER DEFAULT 3,
        ADD COLUMN IF NOT EXISTS preferred_formats JSONB DEFAULT '[]',
        ADD COLUMN IF NOT EXISTS auto_score_drafts BOOLEAN NOT NULL DEFAULT TRUE,
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ
    ;
    """,

    # Index: quickly fetch most recent asset for a post
    """
    CREATE INDEX IF NOT EXISTS idx_carousel_assets_post_id
        ON carousel_assets (post_id, created_at DESC)
    ;
    """,

    # Index: virality score lookups for analytics
    """
    CREATE INDEX IF NOT EXISTS idx_posts_virality_score
        ON posts (virality_score)
        WHERE virality_score IS NOT NULL
    ;
    """,
]


async def run_v2_migration():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=True)

    logger.info("v2_migration_starting")

    async with engine.begin() as conn:
        for i, sql in enumerate(V2_MIGRATIONS, start=1):
            logger.info("running_migration_step", step=i, sql_preview=sql[:80].strip())
            await conn.execute(text(sql))

    logger.info("v2_migration_complete",
                steps_run=len(V2_MIGRATIONS),
                message="All V2 schema changes applied successfully.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_v2_migration())
