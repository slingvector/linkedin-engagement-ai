from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
import os

from app.schemas.talent_schemas import CandidateScoringRequest, OutreachDraftRequest
from app.services.talent_service import TalentAIService

router = APIRouter(prefix="/webhooks/talent", tags=["talent"])
api_key_header = APIKeyHeader(name="X-AI-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    expected_key = os.getenv("AI_MICROSERVICE_API_KEY", "test-ai-key-123")
    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid AI API Key")
    return api_key

@router.post("/score-candidate")
async def score_candidate(
    request: CandidateScoringRequest,
    api_key: str = Depends(verify_api_key)
):
    service = TalentAIService()
    try:
        result = await service.score_candidate(
            request.candidate_profile, 
            request.requisition_description
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/draft-outreach")
async def draft_outreach(
    request: OutreachDraftRequest,
    api_key: str = Depends(verify_api_key)
):
    service = TalentAIService()
    try:
        result = await service.draft_outreach(
            request.candidate_profile,
            request.requisition_description,
            request.my_company_context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
