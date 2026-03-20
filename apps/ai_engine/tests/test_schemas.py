"""Tests for Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas.post_schemas import PostGenerationRequest, PostGenerationResponse
from app.schemas.comment_schemas import CommentGenerationRequest, CommentGenerationResponse


class TestPostSchemas:
    """Validates Post Generation webhook contracts."""

    def test_valid_post_request(self):
        """A complete request should validate successfully."""
        req = PostGenerationRequest(
            user_id="test-uuid",
            topic="The death of mass email automation",
            audience="SaaS Founders",
            framework="contrarian",
        )
        assert req.topic == "The death of mass email automation"
        assert req.framework == "contrarian"
        assert req.tone == "professional_but_conversational"

    def test_missing_required_fields_raises(self):
        """Missing required fields should raise ValidationError."""
        with pytest.raises(ValidationError):
            PostGenerationRequest(
                user_id="test-uuid",
                # missing topic, audience, framework
            )

    def test_topic_max_length(self):
        """Topic over 200 chars should fail."""
        with pytest.raises(ValidationError):
            PostGenerationRequest(
                user_id="test-uuid",
                topic="x" * 201,
                audience="Developers",
                framework="story",
            )

    def test_valid_post_response(self):
        """A valid response should parse correctly."""
        resp = PostGenerationResponse(
            hook="Most engineers don't know this.",
            body_content="Here's what I learned after 10 years...",
            call_to_action="What's your take? Drop it below.",
        )
        assert resp.hook == "Most engineers don't know this."


class TestCommentSchemas:
    """Validates Comment Generation webhook contracts."""

    def test_valid_comment_request(self):
        """A complete comment request should validate."""
        req = CommentGenerationRequest(
            user_id="test-uuid",
            creator_name="John Doe",
            post_content="AI is reshaping the future of recruiting...",
        )
        assert req.creator_name == "John Doe"

    def test_valid_comment_response(self):
        """A valid comment response should parse correctly."""
        resp = CommentGenerationResponse(
            comment_insightful="This aligns with what we saw at...",
            comment_contrarian="I'd push back slightly on this...",
            comment_supportive="We experienced the exact same thing...",
        )
        assert "push back" in resp.comment_contrarian


class TestAIEngineHealth:
    """Test AI Engine health endpoints."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        """GET /health should return 200."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ai_engine"

    @pytest.mark.asyncio
    async def test_readiness_returns_200(self, client):
        """GET /readiness should return 200."""
        response = await client.get("/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_webhook_rejects_without_api_key(self, client):
        """POST to webhook without API key should return 401 (missing) or 403 (wrong)."""
        response = await client.post(
            "/webhooks/generate/post",
            json={
                "user_id": "test",
                "topic": "Test",
                "audience": "Devs",
                "framework": "story",
            },
        )
        # FastAPI's APIKeyHeader returns 401 when header is entirely missing
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_webhook_rejects_wrong_api_key(self, client):
        """POST to webhook with wrong API key should return 403."""
        response = await client.post(
            "/webhooks/generate/post",
            json={
                "user_id": "test",
                "topic": "Test",
                "audience": "Devs",
                "framework": "story",
            },
            headers={"X-AI-API-Key": "wrong_key"},
        )
        assert response.status_code == 403

class TestIdeaSchemas:
    def test_valid_idea_request(self):
        from app.schemas.idea_schemas import IdeaGenerationRequest
        valid_payload = {
            "user_id": "8f8b8e05-24c8-4720-bc5c-4828f0de9161",
            "target_audience": "startup founders",
            "topic_niche": "B2B SaaS churn reduction"
        }
        request = IdeaGenerationRequest(**valid_payload)
        assert request.target_audience == "startup founders"
        assert request.topic_niche == "B2B SaaS churn reduction"

    def test_valid_idea_response(self):
        from app.schemas.idea_schemas import IdeaGenerationResponse
        valid_response = {
            "items": [
                {
                    "idea": "Don't fix your product, fix your onboarding.",
                    "angle": "Argue that churn is mostly a day-1 symptom."
                }
            ]
        }
        resp = IdeaGenerationResponse(**valid_response)
        assert len(resp.items) == 1
        assert resp.items[0].idea.startswith("Don't fix")
