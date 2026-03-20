import asyncio
import structlog
from pathlib import Path

from app.clients.llm_client import openai_client
from app.config import get_settings
from app.schemas.sales_schemas import (
    IntentClassificationRequest,
    IntentClassificationResponse,
    DMDraftRequest,
    DMDraftResponse
)

logger = structlog.get_logger()
settings = get_settings()

class SalesAIService:
    def __init__(self):
        self.prompts_dir = Path(__file__).parent.parent / "prompts"
        self.intent_prompt = self._load_prompt("system_intent_classifier.txt")
        self.dm_prompt = self._load_prompt("system_dm_copilot.txt")

    def _load_prompt(self, filename: str) -> str:
        with open(self.prompts_dir / filename, "r") as f:
            return f.read().strip()
            
    async def classify_intent(self, request: IntentClassificationRequest) -> IntentClassificationResponse:
        logger.info("processing_intent_classification", target=request.prospect_name)
        
        user_message = f"PROSPECT: {request.prospect_name}\nHEADLINE: {request.headline}\n\nBUYING SIGNAL (Comment/Interaction):\n{request.buying_signal}"
        
        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: openai_client.beta.chat.completions.parse(
                model=settings.openrouter_model,
                messages=[
                    {"role": "system", "content": self.intent_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format=IntentClassificationResponse,
                temperature=0.1
            )
        )
        
        result = completion.choices[0].message.parsed
        logger.info("intent_classified", score=result.intent_score)
        return result

    async def draft_dms(self, request: DMDraftRequest) -> DMDraftResponse:
        logger.info("processing_dm_drafts", target=request.prospect_name)
        
        user_message = f"PROSPECT: {request.prospect_name}\nHEADLINE: {request.headline}\n\nBUYING SIGNAL (Comment/Interaction):\n{request.buying_signal}\n\nMY COMPANY/PRODUCT:\n{request.my_company_context}"
        
        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: openai_client.beta.chat.completions.parse(
                model=settings.openrouter_model,
                messages=[
                    {"role": "system", "content": self.dm_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format=DMDraftResponse,
                temperature=0.7 # Need high creativity
            )
        )
        
        result = completion.choices[0].message.parsed
        return result
