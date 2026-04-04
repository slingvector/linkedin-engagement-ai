"""
OAuthState model — persistent CSRF state store for LinkedIn OAuth flows.

Replaces the in-memory dicts that were wiped on restart and not shared
across multiple workers. States expire after 10 minutes.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class OAuthState(Base):
    """
    Stores short-lived CSRF state tokens for OAuth flows.

    - Read-flow (v1): user_id is NULL (user doesn't exist yet)
    - Write-flow (v2): user_id is set (user is already logged in)
    """

    __tablename__ = "oauth_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    state_token = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String(36), nullable=True, comment="Set for write-flow; NULL for read-flow")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
