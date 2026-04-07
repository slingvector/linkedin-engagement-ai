"""
Week Plan Service — AI Engine V2
Generates a full week's content plan from user-defined pillars.
"""

import structlog
from pydantic import BaseModel

from app.services.llm_service import LLMService

logger = structlog.get_logger()

# ── Schemas ──────────────────────────────────────────────────────────────────

class WeekPlanRequest(BaseModel):
    user_id: str
    pillars: list[str]          # e.g. ["AI Automation", "Founder Stories"]
    posts_per_week: int = 4
    preferred_formats: list[str] = ["text", "carousel"]
    top_posts_sample: list[str] = []  # Hook lines of top performing posts for tone calibration

class WeekPlanPost(BaseModel):
    pillar: str
    format: str              # text | carousel | video
    hook: str
    body: str                # 3-5 bullet points or paragraphs
    cta: str
    topic: str               # Concise topic label for the Post model

class WeekPlanResponse(BaseModel):
    posts: list[WeekPlanPost]


# ── Service ──────────────────────────────────────────────────────────────────

class WeekPlanService:
    """
    Generates a balanced N-post content plan for a week.
    Uses the LLMService (Vertex AI / Ollama) to produce structured JSON output.
    """

    SYSTEM_PROMPT = """You are an elite LinkedIn content strategist and ghostwriter.

Your job: generate a balanced weekly content plan that feels personal, expert, and authentic.

Rules:
- Alternate between the provided content pillars evenly
- Rotate formats: maximum 2 plain text posts per week; prioritise carousels and video hooks
- Every hook MUST be ≤ 15 words and must create a curiosity gap or challenge assumptions
- Every body MUST be 3–5 punchy bullet points or short paragraphs (plain LinkedIn formatting, no markdown headers)
- Every CTA asks an open-ended question to spark comments (no "like if you agree")
- Match the voice/tone of the top_posts_sample examples if provided
- Write for professionals (typically startup founders, operators, or senior ICs)

Return STRICT JSON — no markdown, no explanation:
{
  "posts": [
    {
      "pillar": "<string>",
      "format": "text|carousel|video",
      "topic": "<concise topic in ≤5 words>",
      "hook": "<first line, ≤15 words>",
      "body": "<3-5 bullet points or paragraphs>",
      "cta": "<open-ended question or clear call to action>"
    }
  ]
}"""

    def __init__(self, llm_service: LLMService):
        self._llm = llm_service

    async def generate_week_plan(self, request: WeekPlanRequest) -> WeekPlanResponse:
        formats_instruction = ", ".join(request.preferred_formats)
        pillars_str = "\n".join(f"  - {p}" for p in request.pillars)

        tone_section = ""
        if request.top_posts_sample:
            samples = "\n".join(f'  "{h}"' for h in request.top_posts_sample[:3])
            tone_section = f"\nTop performing posts (match this voice/tone):\n{samples}"

        user_prompt = f"""Generate exactly {request.posts_per_week} LinkedIn posts.

Content Pillars:
{pillars_str}

Allowed formats (use these only): {formats_instruction}
{tone_section}

Remember: rotate pillars and formats for a balanced, non-repetitive week."""

        logger.info(
            "week_plan_requested",
            user_id=request.user_id,
            pillars=request.pillars,
            posts_per_week=request.posts_per_week,
        )

        result = await self._llm.generate_structured_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=4000,
            temperature=0.75,
            response_schema=WeekPlanResponse,
        )

        raw_posts = result.get("posts", [])
        posts = [
            WeekPlanPost(
                pillar=p.get("pillar", request.pillars[0]),
                format=p.get("format", "text"),
                topic=p.get("topic", "LinkedIn Post"),
                hook=p.get("hook", ""),
                body=p.get("body", ""),
                cta=p.get("cta", ""),
            )
            for p in raw_posts
        ]

        logger.info(
            "week_plan_generated",
            user_id=request.user_id,
            count=len(posts),
        )

        return WeekPlanResponse(posts=posts)
