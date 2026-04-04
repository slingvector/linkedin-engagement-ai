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
    Abstracted LLM call wrapper supporting Vertex AI and Ollama.
    Follows Open/Closed Principle: swap providers without changing consumers.
    """

    def __init__(self):
        self._settings = get_settings()
        self._yaml_config = get_yaml_config()
        self.provider = self._settings.llm_provider.lower()
        
        self._vertex_client = None
        self._ollama_client = None

        if self.provider == "vertexai":
            if not self._settings.gcp_project_id:
                logger.error("vertexai_initialization_failed", reason="Missing gcp_project_id")
            else:
                self._vertex_client = genai.Client(
                    vertexai=True, 
                    project=self._settings.gcp_project_id, 
                    location=self._settings.gcp_location
                )
                logger.info("vertexai_client_initialized", project=self._settings.gcp_project_id)
        else:
            import openai
            self._ollama_client = openai.AsyncOpenAI(
                base_url=self._settings.ollama_url,
                api_key="ollama"  # Required but ignored by Ollama
            )
            logger.info("ollama_client_initialized", url=self._settings.ollama_url)

    def _get_timeout(self) -> int:
        return self._yaml_config.get("llm", {}).get("timeout_seconds", 30)

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
        max_tokens: int = 2500,
        temperature: float = 0.7,
        response_schema = None,
    ) -> dict:
        """
        Call the configured LLM with strict JSON mode enabled.
        Returns parsed JSON dict.
        """
        logger.info(
            "llm_call_started",
            provider=self.provider,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        raw_text = "{}"

        try:
            if self.provider == "vertexai":
                if not self._vertex_client:
                    raise ValueError("Vertex AI client not configured. Set GCP_PROJECT_ID.")
                    
                model_name = self._settings.vertex_model
                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
                
                response = await self._vertex_client.aio.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=config
                )
                raw_text = response.text.strip() if response.text else "{}"
                logger.info("llm_call_complete", provider="vertexai", model=model_name)

            else:
                # Ollama Route
                model_name = self._settings.ollama_model
                
                # Append schema explicitly to system prompt to aid open-weight models
                enforced_prompt = system_prompt
                if response_schema:
                    # Provide an explicit shape example if Pydantic model is passed
                    schema_json = response_schema.model_json_schema() if hasattr(response_schema, "model_json_schema") else response_schema.schema()
                    enforced_prompt += f"\n\nYou MUST return a valid JSON object matching this schema exactly:\n{json.dumps(schema_json)}\n"

                response = await self._ollama_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": enforced_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=self._get_timeout(),
                )
                raw_text = response.choices[0].message.content
                logger.info("llm_call_complete", provider="ollama", model=model_name)

            # Robust JSON extraction: Find the first '{' and last '}'
            start_idx = raw_text.find('{')
            end_idx = raw_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
                extracted_text = raw_text[start_idx:end_idx+1]
            else:
                extracted_text = "{}"
                
            logger.info("llm_parsed_json", length=len(extracted_text))
            
            with open("/tmp/llm_raw_response.json", "w") as rf:
                rf.write(raw_text)

            return json.loads(extracted_text.strip())
            
        except Exception as e:
            logger.error("llm_generation_failed", error=str(e), provider=self.provider)
            raise RuntimeError(f"All retries failed for LLM ({self.provider}): {e}") from e
