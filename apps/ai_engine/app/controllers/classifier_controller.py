"""
Webhook for bulk Audience Intelligence Classification
"""

from fastapi import APIRouter, Depends, status
import structlog

from app.dependencies import verify_api_key
from app.schemas.classifier_schemas import ClassificationRequest, ClassificationResponse
from app.services.llm_service import LLMService
from app.services.classifier_service import ClassifierService

logger = structlog.get_logger()

# Require X-AI-API-Key for all endpoints in this router
router = APIRouter(
    prefix="/webhooks/classify",
    tags=["webhooks", "audience"],
    dependencies=[Depends(verify_api_key)],
)

def _get_classifier_service() -> ClassifierService:
    return ClassifierService(LLMService())


@router.post(
    "/audience",
    response_model=ClassificationResponse,
    status_code=status.HTTP_200_OK,
)
async def classify_audience_webhook(
    request: ClassificationRequest,
    service: ClassifierService = Depends(_get_classifier_service),
) -> ClassificationResponse:
    """
    Accepts up to 50 LinkedIn profiles and returns a unified persona bucket for each element.
    """
    logger.info("classifier_webhook_received", profile_count=len(request.profiles))
    response = await service.classify_audience(request)
    logger.info("classifier_webhook_completed", successful_classifications=len(response.classifications))
    return response
