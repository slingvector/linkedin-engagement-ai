"""
Extraction service — uses LLM to parse raw HTML/Text into structured LinkedIn posts.
"""

import structlog
from typing import List
from pydantic import BaseModel, Field
from app.services.llm_service import LLMService

logger = structlog.get_logger()

class ExtractedPost(BaseModel):
    post_urn: str = Field(description="LinkedIn activity URN if found, or a unique placeholder")
    author_name: str = Field(description="Name of the person who posted")
    author_profile_id: str = Field(description="The vanity slug or numeric ID from the profile URL")
    text: str = Field(description="The main body text of the post")
    likes: int = Field(default=0)
    comments: int = Field(default=0)

class ExtractionResponse(BaseModel):
    posts: List[ExtractedPost]

class ExtractionService:
    def __init__(self):
        self._llm = LLMService()

    async def extract_posts_from_text(self, text: str, model: str = None) -> List[ExtractedPost]:
        """
        Performs semantic extraction of multiple posts from a raw text blob.
        """
        system_prompt = (
            "You are a LinkedIn data extraction agent. I will provide you with a raw text dump from a LinkedIn feed.\n\n"
            "INSTRUCTIONS:\n"
            "1. Extract EVERY visible post.\n"
            "2. Identify the Author Name, Post Text, and Engagement (Likes/Comments).\n"
            "3. If Likes/Comments are mentioned as 'X others reacted' or 'X comments', extract the number X.\n"
            "4. For the post_urn, use the pattern 'urn:li:activity:[random]' if not explicitly found.\n"
            "5. For author_profile_id, extract the slug (e.g., 'fernando-franco') if found, otherwise use 'unknown'.\n\n"
            "OUTPUT FORMAT:\n"
            "Return a JSON object with a 'posts' array. Example:\n"
            "{\"posts\": [{\"post_urn\": \"...\", \"author_name\": \"...\", \"author_profile_id\": \"...\", \"text\": \"...\", \"likes\": 10, \"comments\": 5}]}"
        )
        
        user_prompt = f"HERE IS THE RAW TEXT DUMP:\n\n{text}"
        
        # We define the schema for Gemini/OpenAI
        response_schema = {
            "type": "object",
            "properties": {
                "posts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "post_urn": {"type": "string"},
                            "author_name": {"type": "string"},
                            "author_profile_id": {"type": "string"},
                            "text": {"type": "string"},
                            "likes": {"type": "integer"},
                            "comments": {"type": "integer"}
                        },
                        "required": ["author_name", "text"]
                    }
                }
            },
            "required": ["posts"]
        }

        try:
            logger.info("extraction_service_call", text_len=len(text))
            result = await self._llm.generate_structured_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
                max_tokens=4096
            )
            
            logger.info("extraction_service_response", posts_count=len(result.get("posts", [])))
            
            posts_data = result.get("posts", [])
            return [ExtractedPost(**p) for p in posts_data]
            
        except Exception as e:
            logger.error("extraction_service_failed", error=str(e), exc_info=True)
            return []
