from pydantic import BaseModel, ConfigDict
from typing import List

class SignalMappingRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    company_name: str
    signal_type: str
    signal_description: str

class SignalMappingResponse(BaseModel):
    mapped_pain_point: str

class SequenceGeneratorRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    company_name: str
    target_persona: str
    pain_point: str
    my_company_context: str

class SequenceStepDraft(BaseModel):
    step_number: int
    subject: str
    body_text: str

class MultiTouchSequenceResponse(BaseModel):
    sequence: List[SequenceStepDraft]
