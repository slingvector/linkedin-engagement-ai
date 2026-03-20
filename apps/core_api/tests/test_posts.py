"""Tests for post generation and CRUD endpoints."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_generate_post_requires_auth(client):
    """POST /api/v1/posts/generate without auth should return 401."""
    response = await client.post(
        "/api/v1/posts/generate",
        json={
            "topic": "AI in recruiting",
            "audience": "HR Leaders",
            "framework": "contrarian",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_posts_requires_auth(client):
    """GET /api/v1/posts without auth should return 401."""
    response = await client.get("/api/v1/posts")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_post_requires_auth(client):
    """GET /api/v1/posts/{id} without auth should return 401."""
    response = await client.get("/api/v1/posts/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_post_requires_auth(client):
    """PATCH /api/v1/posts/{id} without auth should return 401."""
    response = await client.patch(
        "/api/v1/posts/00000000-0000-0000-0000-000000000000",
        json={"status": "approved"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_post_requires_auth(client):
    """DELETE /api/v1/posts/{id} without auth should return 401."""
    response = await client.delete("/api/v1/posts/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401


class TestPostSchemas:
    """Test Pydantic schema validation for post requests."""

    def test_valid_generate_request(self):
        from app.schemas.post import PostGenerateRequest

        req = PostGenerateRequest(
            topic="The future of remote work",
            audience="Tech CEOs",
            framework="story",
        )
        assert req.topic == "The future of remote work"
        assert req.tone == "professional_but_conversational"

    def test_generate_request_topic_max_length(self):
        from pydantic import ValidationError
        from app.schemas.post import PostGenerateRequest

        with pytest.raises(ValidationError):
            PostGenerateRequest(
                topic="x" * 201,
                audience="Devs",
                framework="story",
            )

    def test_post_update_partial(self):
        from app.schemas.post import PostUpdateRequest

        update = PostUpdateRequest(status="approved")
        data = update.model_dump(exclude_unset=True)
        assert data == {"status": "approved"}
        assert "hook" not in data
