import json
from pathlib import Path

import structlog
from pydantic import ValidationError

from app.config import get_settings
from app.schemas.classifier_schemas import ClassificationRequest, ClassificationResponse
from app.services.llm_service import LLMService

logger = structlog.get_logger()


class ClassifierService:
    """
    Orchestrates bulk audience demographic classification.
    """

    def __init__(self, llm_service: LLMService):
        self._llm_service = llm_service
        self._settings = get_settings()

    def _load_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent.parent / "prompts" / "system_classifier.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    async def classify_audience(self, request: ClassificationRequest) -> ClassificationResponse:
        """
        Sends an array of headlines to the LLM to get an array of standard demographic bucket personas.
        """
        system_prompt = self._load_system_prompt()
        
        # We dump the profiles to a JSON string payload to feed the LLM
        profiles_payload = json.dumps([p.model_dump() for p in request.profiles])

        user_prompt = f"Categorize the following profiles:\n\n{profiles_payload}"

        try:
            raw_json_str = await self._llm_service.generate_structured_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0, # Deterministic clustering
            )
            
            resp_dict = json.loads(raw_json_str)

            if "classifications" not in resp_dict:
                # LLM drifted
                logger.warning("classifier_missing_root_key", raw=raw_json_str)
                resp_dict = {"classifications": []}

            return ClassificationResponse(**resp_dict)

        except (ValidationError, json.JSONDecodeError) as e:
            logger.error("classifier_parsing_failed", error=str(e))
            # Fallback on empty response
            return ClassificationResponse(classifications=[])
