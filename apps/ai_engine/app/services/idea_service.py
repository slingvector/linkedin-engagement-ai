"""
Idea generation service — orchestrates AI content idea brainstorms.
"""

from pathlib import Path

import structlog

from app.config import get_yaml_config
from app.schemas.idea_schemas import IdeaGenerationRequest, IdeaGenerationResponse, IdeaResponseItem
from app.services.llm_service import LLMService

logger = structlog.get_logger()

_prompts_dir = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    path = _prompts_dir / filename
    if path.exists():
        return path.read_text().strip()
    return ""


class IdeaService:
    """Generates 5 distinct content ideas for a given niche and audience."""

    def __init__(self, llm_service: LLMService):
        self._llm = llm_service
        self._yaml_config = get_yaml_config()

    async def generate_ideas(self, request: IdeaGenerationRequest) -> IdeaGenerationResponse:
        system_prompt = _load_prompt("system_idea.txt")

        user_prompt = f"""
Target Audience: {request.target_audience}
Topic / Niche: {request.topic_niche}
"""

        prompt_config = self._yaml_config.get("prompts", {}).get("idea_generation", {})

        # The LLM is instructed to return a JSON array of objects.
        # We rely on the LLMService's structured JSON extraction.
        # Because we configured LLMService to parse dicts via response_format={"type": "json_object"},
        # we actually need it to return an array. OpenAI's direct JSON object format requires a top-level object.
        # We will wrap the prompt so that it returns {"items": [{...}]} 
        
        system_prompt += "\n\nCRITICAL JSON WRAPPER: Return exactly this shape: {\"items\": [{\"idea\": \"...\", \"angle\": \"...\"}, ...]}"

        result = await self._llm.generate_structured_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=prompt_config.get("max_output_tokens", 2500),
            temperature=prompt_config.get("temperature", 0.7),
            response_schema=IdeaGenerationResponse,
        )

        logger.info(
            "ideas_generated",
            user_id=request.user_id,
            topic=request.topic_niche,
        )

        items_raw = result.get("items", [])
        items = []
        for item in items_raw:
            items.append(IdeaResponseItem(
                idea=item.get("idea", ""),
                angle=item.get("angle", "")
            ))

        return IdeaGenerationResponse(items=items)
