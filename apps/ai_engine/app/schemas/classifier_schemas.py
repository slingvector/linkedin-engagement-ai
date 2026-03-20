from pydantic import BaseModel, Field


class ProfileItem(BaseModel):
    id: str = Field(..., description="Unique ID of the engager profile")
    headline: str = Field(..., description="Headline or bio of the engager")


class ClassificationRequest(BaseModel):
    """Payload from Core API to classify a batch of engagers."""
    profiles: list[ProfileItem] = Field(..., max_items=50, description="List of profiles to classify")


class ClassificationItem(BaseModel):
    id: str
    persona: str


class ClassificationResponse(BaseModel):
    """Response containing standard personas for each engaged profile."""
    classifications: list[ClassificationItem]
