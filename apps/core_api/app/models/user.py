"""
User model — stores LinkedIn-authenticated users with encrypted tokens.
"""

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class User(Base, UUIDMixin, TimestampMixin):
    """
    Users table.

    Stores LinkedIn profile data and encrypted OAuth tokens.
    subscription_tier gates feature access (free/pro/enterprise).
    preferences stores user-specific AI style rules from the Data Flywheel.
    """

    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    linkedin_id = Column(String(100), unique=True, nullable=False, index=True)
    profile_picture_url = Column(Text, nullable=True)

    # OAuth tokens — encrypted at rest using Fernet
    access_token_encrypted = Column(Text, nullable=True)          # Read-flow token
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    write_access_token_encrypted = Column(Text, nullable=True,    # Write-flow token (carousel publish)
                                          comment="LinkedIn write-flow OAuth access token")

    # Scraper cookies 
    li_at_cookie_encrypted = Column(Text, nullable=True, comment="Browser session cookie for Playwright scraper")

    # LinkedIn Person URN ID (returned by userinfo as 'sub', used in Document Upload API)
    linkedin_person_id = Column(String(100), nullable=True, index=True,
                                comment="LinkedIn numeric person ID for urn:li:person: URN")

    # Feature gating
    subscription_tier = Column(String(50), default="free", nullable=False)

    # AI personalization (populated by Data Flywheel in Phase 2)
    preferences = Column(JSONB, default=dict, nullable=False)

    # External Relationships 
    prospects = relationship("Prospect", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
