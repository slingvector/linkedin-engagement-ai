"""
LLM service — abstraction layer for AI model calls.
Handles model routing (staging/prod), structured outputs, retry logic, and timeouts.
Follows Open/Closed Principle: swap providers without changing consumers.
"""

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import structlog

from app.config import get_settings, get_yaml_config

logger = structlog.get_logger()


class LLMService:
    """
    Abstracted LLM call wrapper.

    Production rules (per project plan):
    1. Strict JSON Mode — use response_format={"type": "json_object"}
    2. Retry Logic — Tenacity with exponential backoff (up to 3 attempts)
    3. Timeout Limits — 15-second hard timeout on all LLM calls
    """

    def __init__(self):
        self._settings = get_settings()
        self._yaml_config = get_yaml_config()
        self._client = AsyncOpenAI(api_key=self._settings.openai_api_key)

    def _get_model(self) -> str:
        """Route to the correct model based on environment."""
        llm_config = self._yaml_config.get("llm", {})
        models = llm_config.get("models", {})
        return models.get(self._settings.environment, "gpt-4o-mini")

    def _get_timeout(self) -> int:
        """Get timeout from config."""
        return self._yaml_config.get("llm", {}).get("timeout_seconds", 15)

    def _get_max_retries(self) -> int:
        """Get retry count from config."""
        return self._yaml_config.get("llm", {}).get("max_retries", 3)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    async def generate_structured_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
    ) -> dict:
        """
        Call the LLM with strict JSON mode enabled.
        Returns parsed JSON dict.

        Implements all three production rules:
        - Strict JSON via response_format
        - Retry via Tenacity decorator
        - Timeout via the client timeout parameter
        """
        model = self._get_model()
        timeout = self._get_timeout()

        logger.info(
            "llm_call_started",
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        response = await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )

        content = response.choices[0].message.content
        usage = response.usage

        logger.info(
            "llm_call_complete",
            model=model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
        )

        import json
        return json.loads(content)
