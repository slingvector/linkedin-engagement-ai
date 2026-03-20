from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
import os

from app.schemas.enterprise_schemas import SignalMappingRequest, SequenceGeneratorRequest
from app.services.enterprise_service import EnterpriseAIService

router = APIRouter(prefix="/webhooks/enterprise", tags=["enterprise"])
api_key_header = APIKeyHeader(name="X-AI-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    expected_key = os.getenv("AI_MICROSERVICE_API_KEY", "test-ai-key-123")
    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid AI API Key")
    return api_key

@router.post("/map-signal")
async def map_signal(
    request: SignalMappingRequest,
    api_key: str = Depends(verify_api_key)
):
    service = EnterpriseAIService()
    try:
        result = await service.map_signal(
            request.company_name, 
            request.signal_type,
            request.signal_description
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-sequence")
async def generate_sequence(
    request: SequenceGeneratorRequest,
    api_key: str = Depends(verify_api_key)
):
    service = EnterpriseAIService()
    try:
        result = await service.generate_sequence(
            request.company_name,
            request.target_persona,
            request.pain_point,
            request.my_company_context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
