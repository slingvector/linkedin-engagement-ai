"""Tests for Creator Radar and Comment Copilot endpoints."""

import pytest
from uuid import uuid4

@pytest.mark.asyncio
async def test_add_creator_requires_auth(client):
    response = await client.post(
        "/api/v1/radar/creators",
        json={
            "linkedin_id": "test_id",
            "profile_url": "https://linkedin.com/in/test",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_creators_requires_auth(client):
    response = await client.get("/api/v1/radar/creators")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_action_desk_requires_auth(client):
    response = await client.get("/api/v1/copilot/feed")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_comments_requires_auth(client):
    response = await client.post(
        "/api/v1/copilot/generate",
        json={"ingested_post_id": str(uuid4())},
    )
    assert response.status_code == 401


class TestCreatorSchemas:
    def test_valid_creator_schema(self):
        from app.schemas.creator import TrackedCreatorCreate
        
        req = TrackedCreatorCreate(
            linkedin_id="john-doe-123",
            profile_url="https://linkedin.com/in/john-doe-123/",
            full_name="John Doe",
        )
        assert req.full_name == "John Doe"
        # Pydantic HttpUrl parses to an object, cast back to string to check
        assert str(req.profile_url) == "https://linkedin.com/in/john-doe-123/"

    def test_invalid_creator_url_raises(self):
        from pydantic import ValidationError
        from app.schemas.creator import TrackedCreatorCreate
        
        with pytest.raises(ValidationError):
            TrackedCreatorCreate(
                linkedin_id="john-doe-123",
                profile_url="not-a-url",  # Should fail validation
                full_name="John Doe",
            )
