"""
Heatmap Service — V2
Computes per-DOW/hour engagement rate heatmaps from real post data.
Falls back to LinkedIn global benchmarks for new users with < 5 posts.
"""

from uuid import UUID
from collections import defaultdict

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

# Global LinkedIn benchmark engagement rates (0.0–1.0 normalised)
# Sourced from Sprout Social / Sprinklr 2025 industry data.
# Key: (day_of_week 0=Mon..6=Sun, hour 0-23) → relative rate
_GLOBAL_BENCHMARKS: dict[tuple[int, int], float] = {
    (0, 8): 0.55,  (0, 9): 0.70,  (0, 10): 0.72, (0, 11): 0.65,
    (1, 8): 0.75,  (1, 9): 0.92,  (1, 10): 0.98, (1, 11): 0.90, (1, 12): 0.80,
    (2, 8): 0.70,  (2, 9): 0.88,  (2, 10): 0.95, (2, 11): 0.88, (2, 12): 0.78,
    (3, 8): 0.75,  (3, 9): 0.94,  (3, 10): 0.96, (3, 11): 0.87,
    (4, 8): 0.60,  (4, 9): 0.75,  (4, 10): 0.78,
    (5, 9): 0.20,  (5, 10): 0.22,
    (6, 9): 0.15,  (6, 10): 0.18,
}

_DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _build_benchmark_heatmap() -> dict:
    """Build the global benchmark structure in the same shape as the real query."""
    heatmap: dict[str, dict[str, float]] = {d: {} for d in _DAY_NAMES}
    for (dow, hour), rate in _GLOBAL_BENCHMARKS.items():
        day_name = _DAY_NAMES[dow]
        heatmap[day_name][str(hour)] = round(rate, 3)
    return heatmap


def _best_slots(heatmap: dict, n: int = 5) -> list[dict]:
    """Extract top N slots sorted by rate."""
    slots = []
    for day, hours in heatmap.items():
        for hour_str, rate in hours.items():
            slots.append({"day": day, "hour": int(hour_str), "avg_engagement_rate": rate})
    return sorted(slots, key=lambda x: x["avg_engagement_rate"], reverse=True)[:n]


def _worst_slots(heatmap: dict, n: int = 3) -> list[dict]:
    slots = []
    for day, hours in heatmap.items():
        for hour_str, rate in hours.items():
            slots.append({"day": day, "hour": int(hour_str), "avg_engagement_rate": rate})
    return sorted(slots, key=lambda x: x["avg_engagement_rate"])[:n]


class HeatmapService:
    """
    Computes the engagement heatmap for a user's content calendar.

    Query strategy:
      - Pulls published posts with impression data for the last N weeks.
      - Groups by ISO day-of-week (1=Mon..7=Sun → normalised to 0=Mon) and hour.
      - Calculates weighted engagement rate: (likes + comments*3) / impressions
      - Normalises to 0.0–1.0 relative to the user's own maximum.
      - Falls back to global LinkedIn benchmarks if fewer than MIN_DATA_POSTS posts exist.
    """

    MIN_DATA_POSTS = 5

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_heatmap(self, user_id: UUID, weeks: int = 8) -> dict:
        """
        Returns the full heatmap response.
        Shape: { heatmap, best_slots, worst_slots, data_source }
        """
        raw = await self._query_raw(user_id, weeks)

        if len(raw) < self.MIN_DATA_POSTS:
            logger.info(
                "heatmap_using_global_benchmarks",
                user_id=str(user_id),
                sample_size=len(raw),
            )
            heatmap = _build_benchmark_heatmap()
            data_source = "global_benchmark"
        else:
            heatmap = self._build_personal_heatmap(raw)
            data_source = "personal"
            logger.info(
                "heatmap_using_personal_data",
                user_id=str(user_id),
                sample_size=len(raw),
            )

        return {
            "heatmap": heatmap,
            "best_slots": _best_slots(heatmap),
            "worst_slots": _worst_slots(heatmap),
            "data_source": data_source,
            "sample_size": len(raw),
        }

    async def _query_raw(self, user_id: UUID, weeks: int) -> list[dict]:
        """Raw SQL — groups by DOW+hour, calculates weighted engagement rate."""
        sql = text("""
            SELECT
                -- ISODOW: 1=Monday, 7=Sunday
                EXTRACT(ISODOW FROM published_at)::int - 1  AS dow,
                EXTRACT(HOUR FROM published_at)::int         AS hour,
                COUNT(*)                                     AS post_count,
                AVG(
                    CASE
                        WHEN impressions > 0
                        THEN (likes + comments_count * 3.0) / impressions
                        ELSE 0
                    END
                )                                            AS avg_rate
            FROM posts
            WHERE
                user_id    = :user_id
                AND status = 'published'
                AND published_at IS NOT NULL
                AND impressions > 0
                AND published_at > NOW() - INTERVAL ':weeks weeks'
            GROUP BY dow, hour
            ORDER BY avg_rate DESC
        """)
        # SQLAlchemy text() doesn't interpolate inside strings, use replace for interval
        safe_sql = text(
            sql.text.replace(":weeks weeks", f"{weeks} weeks")
        )
        result = await self._db.execute(safe_sql, {"user_id": user_id})
        return [
            {"dow": row.dow, "hour": row.hour, "post_count": row.post_count, "avg_rate": float(row.avg_rate)}
            for row in result.fetchall()
        ]

    def _build_personal_heatmap(self, raw: list[dict]) -> dict:
        """Normalise personal data to 0.0–1.0 and build heatmap dict."""
        if not raw:
            return {d: {} for d in _DAY_NAMES}

        max_rate = max(r["avg_rate"] for r in raw) or 1.0

        heatmap: dict[str, dict[str, float]] = defaultdict(dict)
        for row in raw:
            day_name = _DAY_NAMES[int(row["dow"])]
            normalised = round(float(row["avg_rate"]) / max_rate, 3)
            heatmap[day_name][str(row["hour"])] = normalised

        # Ensure all days present
        for day in _DAY_NAMES:
            if day not in heatmap:
                heatmap[day] = {}

        return dict(heatmap)
