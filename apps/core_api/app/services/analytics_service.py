import httpx
import structlog
from uuid import UUID

from app.config import get_settings
from app.repositories.analytics_repository import AnalyticsRepository
from app.models.analytics import Engager

logger = structlog.get_logger()


class AnalyticsService:
    def __init__(self, analytics_repo: AnalyticsRepository):
        self.repo = analytics_repo
        self.settings = get_settings()

    async def get_dashboard_metrics(self, user_id: UUID) -> dict:
        """
        Aggregates data into a strict format compliant with Recharts line/pie objects.
        """
        timeline = await self.repo.get_metrics_timeline(user_id)
        raw_demographics = await self.repo.get_audience_demographics(user_id)

        # Reformat timeline for Recharts: [{ date: '2023-01-01', impressions: 400 }]
        formatted_timeline = [
            {
                "date": metric.recorded_at.strftime("%Y-%m-%d"),
                "impressions": metric.impressions,
                "likes": metric.likes,
                "comments": metric.comments
            }
            for metric in timeline
        ]

        # Reformat pie chart data
        formatted_demographics = [
            {"name": persona, "value": count}
            for persona, count in raw_demographics.items()
        ]

        return {
            "timeline": formatted_timeline,
            "demographics": formatted_demographics,
        }

    async def process_unclassified_engagers(self):
        """
        Background worker task. Flushes batches of unclassified Engagers to the AI Engine for mapping.
        """
        unclassified = await self.repo.get_unclassified_engagers(limit=50)
        if not unclassified:
            return

        payload = {
            "profiles": [
                {"id": str(e.id), "headline": e.headline} 
                for e in unclassified
            ]
        }

        url = f"{self.settings.ai_engine_url}/webhooks/classify/audience"
        headers = {"X-AI-API-Key": self.settings.ai_engine_api_key}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                classifications = response.json().get("classifications", [])
                
                # Bulk insert mappings
                for mapping in classifications:
                    engager_id = UUID(mapping["id"])
                    persona = mapping["persona"]
                    await self.repo.create_classification(engager_id, persona)
                    
                logger.info("audience_classification_chunk_processed", processed=len(classifications))

        except Exception as e:
            logger.error("audience_classification_failed", error=str(e))
