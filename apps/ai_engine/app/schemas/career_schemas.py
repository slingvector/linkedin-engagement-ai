from pydantic import BaseModel, Field
from typing import List

class ResumeBulletPoint(BaseModel):
    original_point: str = Field(..., description="The original bullet point from the resume.")
    optimized_point: str = Field(..., description="The rewritten bullet point incorporating keywords from the job description and focusing on impactful metrics.")
    reasoning: str = Field(..., description="A brief explanation of why this change makes the user a stronger candidate for this specific job.")

class ResumeOptimizationRequest(BaseModel):
    job_description: str = Field(..., description="The raw text of the target job description.")
    resume_text: str = Field(..., description="The raw extracted text of the user's resume.")

class ResumeOptimizationResponse(BaseModel):
    optimized_bullets: List[ResumeBulletPoint] = Field(..., description="A mapping of old bullet points to new optimized bullet points.")
    overall_match_score: int = Field(..., ge=0, le=100, description="An estimated 0-100 score of how well the original resume matches the job.")

class CoverLetterRequest(BaseModel):
    job_description: str = Field(..., description="The raw text of the target job description.")
    resume_text: str = Field(..., description="The raw extracted text of the user's resume.")
    company_name: str = Field(..., description="The name of the company.")
    role_title: str = Field(..., description="The title of the role being applied for.")

class CoverLetterResponse(BaseModel):
    cover_letter_body: str = Field(..., description="The highly contextual, generated cover letter body. Should NOT include header/footer boilerplate like addresses.")
    hooks_used: List[str] = Field(..., description="A list of specific intersection points used to hook the recruiter (e.g., 'Leveraged my 3 years of Postgres experience to address your scaling requirements').")
