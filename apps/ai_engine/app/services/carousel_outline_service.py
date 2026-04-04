"""
Carousel Outline Service — AI Engine V2
Generates a 7-slide LinkedIn carousel outline from a topic and audience.
"""

import structlog
from pydantic import BaseModel

from app.services.llm_service import LLMService

logger = structlog.get_logger()


# ── Schemas ───────────────────────────────────────────────────────────────────

class CarouselOutlineRequest(BaseModel):
    user_id: str
    topic: str
    audience: str
    tone: str = "professional_but_conversational"
    slide_count: int = 7


class Slide(BaseModel):
    slide_number: int
    headline: str          # ≤ 8 words — the bold text on the slide
    body: str              # 2–3 lines of supporting copy
    visual_suggestion: str # What to put in the image area


class CarouselOutlineResponse(BaseModel):
    slides: list[Slide]
    cover_hook: str        # The first slide's scroll-stopping hook (also goes in post caption)
    cta_slide_text: str    # Slide 7 CTA text


# ── Service ───────────────────────────────────────────────────────────────────

class CarouselOutlineService:
    """
    Generates a structured 7-slide LinkedIn carousel outline.

    Slide structure:
      Slide 1: Provocative hook — curiosity gap or a contrarian stat
      Slides 2–6: One actionable insight per slide (≤ 40 words)
      Slide 7: CTA + teaser for the next carousel
    """

    SYSTEM_PROMPT = """You are a LinkedIn carousel expert and visual content strategist.

Your job: generate a 7-slide LinkedIn carousel outline that makes people swipe to the end.

SLIDE RULES:
- Slide 1: A scroll-stopping hook. Curiosity gap, contrarian stat, or bold claim (≤ 8 words headline)
- Slides 2–6: One crystal-clear actionable insight per slide. Short. Scannable. Mobile-first.
  Each headline ≤ 8 words. Each body ≤ 40 words (2–3 punchy sentences)
- Slide 7: CTA slide — tell them what to do next + tease the next carousel
- visual_suggestion: describe exactly what image/icon/chart belongs on this slide (1 sentence)

Return STRICT JSON — no markdown, no explanation:
{
  "cover_hook": "<the slide 1 headline, ≤ 8 words — also used as post caption opener>",
  "cta_slide_text": "<slide 7 CTA text, ≤ 20 words>",
  "slides": [
    {
      "slide_number": 1,
      "headline": "<≤ 8 words>",
      "body": "<≤ 40 words>",
      "visual_suggestion": "<one sentence>"
    }
  ]
}"""

    def __init__(self, llm_service: LLMService):
        self._llm = llm_service

    async def generate_outline(self, request: CarouselOutlineRequest) -> CarouselOutlineResponse:
        user_prompt = f"""Generate a {request.slide_count}-slide LinkedIn carousel on this topic:

Topic: {request.topic}
Target Audience: {request.audience}
Tone: {request.tone}

Make it impossible to stop swiping."""

        logger.info(
            "carousel_outline_requested",
            user_id=request.user_id,
            topic=request.topic,
        )

        result = await self._llm.generate_structured_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=3000,
            temperature=0.7,
            response_schema=CarouselOutlineResponse,
        )

        raw_slides = result.get("slides", [])
        slides = [
            Slide(
                slide_number=s.get("slide_number", i + 1),
                headline=s.get("headline", ""),
                body=s.get("body", ""),
                visual_suggestion=s.get("visual_suggestion", ""),
            )
            for i, s in enumerate(raw_slides)
        ]

        response = CarouselOutlineResponse(
            slides=slides,
            cover_hook=result.get("cover_hook", slides[0].headline if slides else ""),
            cta_slide_text=result.get("cta_slide_text", "Follow for more →"),
        )

        logger.info(
            "carousel_outline_generated",
            user_id=request.user_id,
            slide_count=len(slides),
        )

        return response
