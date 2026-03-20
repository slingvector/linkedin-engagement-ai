"""
Comment generation service — orchestrates AI comment creation.
"""

from pathlib import Path

import structlog

from app.config import get_yaml_config
from app.schemas.comment_schemas import CommentGenerationRequest, CommentGenerationResponse
from app.services.llm_service import LLMService

logger = structlog.get_logger()

_prompts_dir = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    path = _prompts_dir / filename
    if path.exists():
        return path.read_text().strip()
    return ""


class CommentService:
    """Generates 3 distinct comment strategies for a given LinkedIn post."""

    def __init__(self, llm_service: LLMService):
        self._llm = llm_service
        self._yaml_config = get_yaml_config()

    def _get_blocklist(self) -> str:
        """Get forbidden comment phrases from config."""
        blocklist = self._yaml_config.get("blocklist", {})
        forbidden = blocklist.get("forbidden_comment_phrases", [])
        return ", ".join(f'"{w}"' for w in forbidden)

    async def generate_comments(self, request: CommentGenerationRequest) -> CommentGenerationResponse:
        """
        Generate comments for a tracked creator's post.
        """
        system_prompt = _load_prompt("system_comment.txt")
        blocklist_str = self._get_blocklist()

        user_prompt = f"""
Creator Name: {request.creator_name}

Original Post Content:
---
{request.post_content}
---

STRICT NEGATIVE BLOCKLIST — NEVER use these phrases:
{blocklist_str}
"""

        prompt_config = self._yaml_config.get("prompts", {}).get("comment_generation", {})

        # Call LLM
        result = await self._llm.generate_structured_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=prompt_config.get("max_output_tokens", 800),
            temperature=prompt_config.get("temperature", 0.6),
        )

        logger.info(
            "comments_generated",
            user_id=request.user_id,
            creator_name=request.creator_name,
        )

        return CommentGenerationResponse(
            comment_insightful=result.get("comment_insightful", ""),
            comment_contrarian=result.get("comment_contrarian", ""),
            comment_supportive=result.get("comment_supportive", ""),
        )
