from pydantic import BaseModel, ConfigDict
from typing import Optional

class CandidateScoringRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    candidate_profile: str
    requisition_description: str

class CandidateScoringResponse(BaseModel):
    match_score: int
    fit_rationale: str

class OutreachDraftRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    candidate_profile: str
    requisition_description: str
    my_company_context: str

class OutreachDraftResponse(BaseModel):
    subject_line: str
    draft_1: str
    draft_2: str
