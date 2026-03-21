"""
Feedback model — stores user interactions with AI generated comments.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer

from app.models.base import Base, UUIDMixin, TimestampMixin


class CommentFeedback(Base, UUIDMixin, TimestampMixin):
    """
    CommentFeedback table.

    Captures which comment was generated, what the user edited it to,
    and whether it was used. Serves as training data for future fine-tuning.
    """

    __tablename__ = "comment_feedbacks"

    # The ID of the LinkedIn post they are commenting on
    post_id = Column(String(100), nullable=True, index=True)

    # The AI generated text
    original_generated_comment = Column(Text, nullable=False)

    # What the user actually posted (could be edited or the same)
    final_user_edited_comment = Column(Text, nullable=True)

    # Whether this comment was actually pushed/copied by the user
    was_used = Column(Boolean, default=False, nullable=False)

    # Engagement metrics (populated later if we track responses)
    engagement_likes = Column(Integer, default=0, nullable=False)
    engagement_replies = Column(Integer, default=0, nullable=False)
