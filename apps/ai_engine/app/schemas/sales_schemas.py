from pydantic import BaseModel, Field

class IntentClassificationRequest(BaseModel):
    prospect_name: str = Field(..., description="The name of the prospect.")
    headline: str = Field(None, description="The prospect's headline.")
    buying_signal: str = Field(..., description="The text of the prospect's comment or interaction.")

class IntentClassificationResponse(BaseModel):
    intent_score: int = Field(..., ge=0, le=100, description="The graded score from 0 to 100 on how likely the prospect is to buy.")
    rationale: str = Field(..., description="A 1-sentence reasoning for the assigned score.")

class DMDraftRequest(BaseModel):
    prospect_name: str = Field(..., description="The name of the prospect.")
    headline: str = Field(None, description="The prospect's headline.")
    buying_signal: str = Field(..., description="The context of what the prospect said.")
    my_company_context: str = Field(..., description="Context regarding my own company or product to pivot the prospect towards.")

class DMDraftResponse(BaseModel):
    draft_1: str = Field(..., description="A direct, pitch-heavy DM opener.")
    draft_2: str = Field(..., description="A soft, relationship-building DM opener asking a question about their pain point.")
    draft_3: str = Field(..., description="An extremely short, casual DM opener optimizing for a quick reply.")
