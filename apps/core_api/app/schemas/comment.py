from pydantic import BaseModel
from typing import Optional

class CommentFeedbackCreate(BaseModel):
    post_id: Optional[str] = None
    original_generated_comment: str
    final_user_edited_comment: Optional[str] = None
    was_used: bool = False
    engagement_likes: int = 0
    engagement_replies: int = 0
