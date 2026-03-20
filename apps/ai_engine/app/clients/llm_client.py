import os
from openai import AsyncOpenAI

# Single unified async client for structured output generation tools
openai_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "dummy_key_for_mock_execution")
)
