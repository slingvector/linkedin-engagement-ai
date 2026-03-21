"""
Post generation service — orchestrates AI post creation.
"""

from pathlib import Path

import yaml
import structlog

from app.config import get_yaml_config
from app.schemas.post_schemas import PostGenerationRequest, PostGenerationResponse
from app.services.llm_service import LLMService

logger = structlog.get_logger()

# Load prompt templates from files at module level
_prompts_dir = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    path = _prompts_dir / filename
    if path.exists():
        return path.read_text().strip()
    return ""


class PostService:
    """Orchestrates AI post generation using the appropriate framework template."""

    def __init__(self, llm_service: LLMService):
        self._llm = llm_service
        self._yaml_config = get_yaml_config()

    def _get_blocklist(self) -> str:
        """Build the negative blocklist string from YAML config."""
        blocklist = self._yaml_config.get("blocklist", {})
        forbidden = blocklist.get("forbidden_words", [])
        return ", ".join(f'"{w}"' for w in forbidden)

    async def generate_post(self, request: PostGenerationRequest) -> PostGenerationResponse:
        """
        Generate a structured post using the specified framework.

        Flow:
        1. Load system prompt + framework-specific template
        2. Inject topic, audience, tone, blocklist, and user preferences
        3. Call LLM with strict JSON mode
        4. Parse and return PostGenerationResponse
        """
        # Load prompts
        system_prompt = _load_prompt("system_post.txt")
        framework_prompt = _load_prompt(f"framework_{request.framework}.txt")

        # Build negative blocklist
        blocklist_str = self._get_blocklist()

        # Build user prompt with context injection
        user_prompt = f"""
Topic: {request.topic}
Target Audience: {request.audience}
Tone: {request.tone or 'professional but conversational'}
Framework: {request.framework}

Framework-Specific Instructions:
{framework_prompt}

STRICT NEGATIVE BLOCKLIST — NEVER use these words or phrases:
{blocklist_str}
"""

        # Inject user preferences from Data Flywheel (if available)
        if request.user_preferences:
            style_rules = request.user_preferences.get("style_rules", [])
            if style_rules:
                rules_str = "\n".join(f"- {rule}" for rule in style_rules)
                user_prompt += f"""
User's Personalized Style Rules (MANDATORY):
{rules_str}
"""

        # Get prompt config from YAML
        prompt_config = self._yaml_config.get("prompts", {}).get("post_generation", {})

        # Call LLM
        result = await self._llm.generate_structured_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=prompt_config.get("max_output_tokens", 1500),
            temperature=prompt_config.get("temperature", 0.7),
            response_schema=PostGenerationResponse,
        )

        logger.info(
            "post_generated",
            user_id=request.user_id,
            framework=request.framework,
        )

        return PostGenerationResponse(
            hook=result.get("hook", ""),
            body_content=result.get("body_content", ""),
            call_to_action=result.get("call_to_action", ""),
        )
