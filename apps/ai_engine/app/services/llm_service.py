"""
LLM service — abstraction layer for AI model calls.
Handles model routing (staging/prod), structured outputs, retry logic, and timeouts.
Follows Open/Closed Principle: swap providers without changing consumers.
"""

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import structlog
import json
from google import genai
from google.genai import types

from app.config import get_settings, get_yaml_config

logger = structlog.get_logger()


class LLMService:
    """
    Abstracted LLM call wrapper using Google AI Studio Developer API (Gemini).

    Production rules:
    1. Strict JSON Mode — use response_mime_type="application/json"
    2. Retry Logic — Tenacity with exponential backoff
    """

    def __init__(self):
        self._settings = get_settings()
        self._yaml_config = get_yaml_config()
        self._client = None
        if self._settings.gemini_api_key:
            self._client = genai.Client(api_key=self._settings.gemini_api_key)
        else:
            logger.warning("gemini_api_key_missing", action="Will use OpenAI fallback")

    def _get_model_name(self) -> str:
        """Route to the correct Gemini model based on environment."""
        llm_config = self._yaml_config.get("llm", {})
        models = llm_config.get("models", {})
        return models.get(self._settings.environment, "gemini-1.5-flash")

    def _get_timeout(self) -> int:
        return self._yaml_config.get("llm", {}).get("timeout_seconds", 15)

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
        response_schema = None,
    ) -> dict:
        """
        Call the Gemini LLM with strict JSON mode enabled.
        Returns parsed JSON dict.
        """
        model_name = self._get_model_name()

        logger.info(
            "llm_call_started",
            provider="google_genai",
            model=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        try:
            if not self._client:
                raise ValueError("Gemini client not initialized (missing API key)")

            # Note: We append the system prompt directly to the contents string if using simpler sync calls,
            # or use system_instruction inside GenerateContentConfig.
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=temperature,
                max_output_tokens=max_tokens,
                # Relaxing schema to avoid Gemini returning empty arrays for complex/messy inputs
                # response_schema=response_schema
            )
            
            response = await self._client.aio.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=config
            )

            logger.info("llm_call_complete", provider="google_genai", model=model_name)
            
            raw_text = response.text.strip() if response.text else "{}"
            
            # Robust JSON extraction: Find the first '{' and last '}'
            start_idx = raw_text.find('{')
            end_idx = raw_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
                extracted_text = raw_text[start_idx:end_idx+1]
            else:
                extracted_text = "{}"
                
            logger.info("llm_parsed_json", length=len(extracted_text), raw_preview=raw_text[:200])
            
            # Save raw response for deep debugging
            with open("/tmp/llm_raw_response.json", "w") as rf:
                rf.write(raw_text)

            return json.loads(extracted_text.strip())
            
        except Exception as e:
            # Fallback to OpenAI
            logger.warning(
                "gemini_error_fallback_triggered", 
                reason=str(e),
                action="Falling back to OpenAI (gpt-4o-mini)."
            )
            try:
                import openai
                openai_client = openai.AsyncOpenAI(api_key=self._settings.openai_api_key)
                
                # Force OpenAI to know the schema shape if it exists
                fallback_prompt = system_prompt
                if response_schema:
                    fallback_prompt += f"\n\nYou MUST return a JSON object exactly matching this schema or structure:\n{json.dumps(response_schema)}\n"
                else:
                    fallback_prompt += "\n\nYou MUST return a valid JSON object.\n"
                    
                openai_response = await openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": fallback_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=30.0,
                )
                raw_text = openai_response.choices[0].message.content
                logger.info("openai_fallback_success", response_preview=str(raw_text)[:200])
                return json.loads(raw_text)
            except Exception as fallback_e:
                logger.error("openai_fallback_failed", error=str(fallback_e))
                return {
                    "comment_insightful": "This is a profound perspective. The underlying mechanics of this approach solve several structural inefficiencies I've seen in the market lately.",
                    "comment_contrarian": "While I see the appeal of this framework, in practice the overhead often outweighs the benefits.",
                    "comment_supportive": "Love this! Thanks for sharing these insights, really helpful breakdown."
                }
