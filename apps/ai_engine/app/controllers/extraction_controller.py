"""
Controller for semantic data extraction from raw content.
"""

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import List

from app.services.extraction_service import ExtractionService, ExtractedPost
from app.config import get_settings

router = APIRouter(prefix="/webhooks/extract", tags=["Extraction"])
extraction_service = ExtractionService()

class ExtractionRequest(BaseModel):
    html_text: str
    model: str = None

class ExtractionResponse(BaseModel):
    posts: List[ExtractedPost]

@router.post("/posts", response_model=ExtractionResponse)
async def webhook_extract_posts(
    request: ExtractionRequest,
    x_ai_api_key: str = Header(None)
):
    """
    Semantic extraction of posts from raw HTML/Text.
    Used by the ingestion worker as Tier 2 fallback.
    """
    settings = get_settings()
    if x_ai_api_key != settings.ai_engine_api_key:
        raise HTTPException(status_code=401, detail="Invalid AI API Key")

    posts = await extraction_service.extract_posts_from_text(
        text=request.html_text,
        model=request.model
    )
    
    return ExtractionResponse(posts=posts)
