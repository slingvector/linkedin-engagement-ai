from fastapi import APIRouter, Depends, Security
import structlog

from app.dependencies import verify_api_key
from app.services.sales_service import SalesAIService
from app.schemas.sales_schemas import (
    IntentClassificationRequest,
    IntentClassificationResponse,
    DMDraftRequest,
    DMDraftResponse
)

logger = structlog.get_logger()

router = APIRouter(
    prefix="/webhooks/sales",
    tags=["Sales Intelligence"],
    dependencies=[Security(verify_api_key)]
)

def get_sales_service() -> SalesAIService:
    return SalesAIService()

@router.post("/classify-intent", response_model=IntentClassificationResponse)
async def classify_intent(
    request: IntentClassificationRequest,
    service: SalesAIService = Depends(get_sales_service)
):
    """
    Grades a prospect's interaction from 0-100 based on B2B buying signals.
    """
    return await service.classify_intent(request)


@router.post("/draft-dm", response_model=DMDraftResponse)
async def draft_dm(
    request: DMDraftRequest,
    service: SalesAIService = Depends(get_sales_service)
):
    """
    Generates 3 contextual transition messages (Comment-to-DM) using local product knowledge.
    """
    return await service.draft_dms(request)
