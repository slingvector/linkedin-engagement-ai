from pydantic import BaseModel, Field

class IdeaGenerationRequest(BaseModel):
    user_id: str
    target_audience: str = Field(..., max_length=100)
    topic_niche: str = Field(..., max_length=100)

class IdeaResponseItem(BaseModel):
    idea: str
    angle: str

class IdeaGenerationResponse(BaseModel):
    items: list[IdeaResponseItem]
