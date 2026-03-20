from fastapi import APIRouter, Depends, Security
import structlog

from app.dependencies import verify_api_key
from app.services.career_service import CareerService
from app.schemas.career_schemas import (
    ResumeOptimizationRequest,
    ResumeOptimizationResponse,
    CoverLetterRequest,
    CoverLetterResponse
)

logger = structlog.get_logger()

router = APIRouter(
    prefix="/webhooks/career",
    tags=["Career Intelligence"],
    dependencies=[Security(verify_api_key)]
)

def get_career_service() -> CareerService:
    return CareerService()

@router.post("/optimize-resume", response_model=ResumeOptimizationResponse)
async def optimize_resume(
    request: ResumeOptimizationRequest,
    service: CareerService = Depends(get_career_service)
):
    """
    Accepts raw Job Description and Resume JSONs. 
    Returns restructured resume bullet points optimized for passing the ATS and aligning with required skills.
    """
    return await service.optimize_resume(request)


@router.post("/cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter(
    request: CoverLetterRequest,
    service: CareerService = Depends(get_career_service)
):
    """
    Generates a deeply contextualized cover letter mapping the applicant's experience to the specific pain points of the business.
    """
    return await service.draft_cover_letter(request)
