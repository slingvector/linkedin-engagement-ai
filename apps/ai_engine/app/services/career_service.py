import asyncio
import structlog
from pathlib import Path

from app.clients.llm_client import openai_client
from app.config import get_settings
from app.schemas.career_schemas import (
    ResumeOptimizationRequest,
    ResumeOptimizationResponse,
    CoverLetterRequest,
    CoverLetterResponse
)

logger = structlog.get_logger()
settings = get_settings()

class CareerService:
    def __init__(self):
        self.prompts_dir = Path(__file__).parent.parent / "prompts"
        self.resume_prompt = self._load_prompt("system_resume_optimizer.txt")
        self.cover_letter_prompt = self._load_prompt("system_cover_letter.txt")

    def _load_prompt(self, filename: str) -> str:
        with open(self.prompts_dir / filename, "r") as f:
            return f.read().strip()
            
    async def optimize_resume(self, request: ResumeOptimizationRequest) -> ResumeOptimizationResponse:
        logger.info("processing_resume_optimization")
        
        user_message = f"JOB DESCRIPTION:\n{request.job_description}\n\nCANDIDATE RESUME:\n{request.resume_text}"
        
        # We run litellm in a threadpool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: openai_client.beta.chat.completions.parse(
                model=settings.openrouter_model,
                messages=[
                    {"role": "system", "content": self.resume_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format=ResumeOptimizationResponse,
                temperature=0.3
            )
        )
        
        result = completion.choices[0].message.parsed
        logger.info("resume_optimization_complete", matched_score=result.overall_match_score)
        return result

    async def draft_cover_letter(self, request: CoverLetterRequest) -> CoverLetterResponse:
        logger.info("processing_cover_letter_generation", company=request.company_name, role=request.role_title)
        
        user_message = f"COMPANY: {request.company_name}\nROLE: {request.role_title}\n\nJOB DESCRIPTION:\n{request.job_description}\n\nCANDIDATE RESUME:\n{request.resume_text}"
        
        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: openai_client.beta.chat.completions.parse(
                model=settings.openrouter_model,
                messages=[
                    {"role": "system", "content": self.cover_letter_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format=CoverLetterResponse,
                temperature=0.7 # slightly more creative for the cover letter
            )
        )
        
        result = completion.choices[0].message.parsed
        logger.info("cover_letter_generation_complete", hooks_count=len(result.hooks_used))
        return result
