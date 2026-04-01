"""
Virality Score Service — AI Engine V2
Scores a LinkedIn post draft 0-100 based on hook, readability, value, and CTA.
Returns 3 alternative hooks ranked by predicted engagement.
"""

import structlog
from pydantic import BaseModel

from app.services.llm_service import LLMService

logger = structlog.get_logger()


# ── Schemas ──────────────────────────────────────────────────────────────────

class ScoreRequest(BaseModel):
    user_id: str
    post_id: str
    draft_text: str               # Full post text (hook + body + CTA)
    top_posts_sample: list[str] = []  # Hook lines of user's top performers

class ScoreBreakdown(BaseModel):
    hook_strength: int    # 0-30
    readability: int      # 0-20
    value_density: int    # 0-30
    cta_quality: int      # 0-20

class HookAlternative(BaseModel):
    hook: str
    predicted_score: int  # 0-100

class ScoreResponse(BaseModel):
    total_score: int
    breakdown: ScoreBreakdown
    hook_alternatives: list[HookAlternative]
    reasoning: str


# ── Service ──────────────────────────────────────────────────────────────────

class ViralityScoreService:
    """
    Scores a LinkedIn draft post on 4 dimensions:
      - Hook Strength (0-30): curiosity gap, contrarian, pattern interrupt
      - Readability (0-20): short lines, white space, mobile-friendly
      - Value Density (0-30): one clear insight per paragraph, actionable
      - CTA Quality (0-20): open-ended question, genuine conversation starter

    Also generates 3 alternative hooks ranked by predicted score.
    """

    SYSTEM_PROMPT = """You are a LinkedIn algorithm expert and conversion copywriter.

Your job: score the following LinkedIn draft post and generate 3 superior hook alternatives.

SCORING RUBRIC (return integers, not floats):
- hook_strength (0-30): Does the first line stop the scroll? Does it create curiosity, challenge assumptions, or reveal a surprising stat?
- readability (0-20): Short sentences? Line breaks every 2-3 lines? Easy to skim on mobile? No walls of text?
- value_density (0-30): Every sentence teaches something actionable. No filler. No vague platitudes.
- cta_quality (0-20): Does the CTA ask a genuine open-ended question? Does it invite debate, not just likes?

HOOK ALTERNATIVES:
Generate exactly 3 improved first-line hooks for the same post. Each must be ≤ 15 words.
Assign each a predicted_score (0-100) based on how well the improved hook would perform.

REASONING: Write 1-2 sentences explaining the main weaknesses and how to fix them.

Return STRICT JSON — no markdown:
{
  "total_score": <int 0-100>,
  "breakdown": {
    "hook_strength": <int 0-30>,
    "readability": <int 0-20>,
    "value_density": <int 0-30>,
    "cta_quality": <int 0-20>
  },
  "hook_alternatives": [
    {"hook": "<string>", "predicted_score": <int 0-100>},
    {"hook": "<string>", "predicted_score": <int 0-100>},
    {"hook": "<string>", "predicted_score": <int 0-100>}
  ],
  "reasoning": "<string>"
}"""

    def __init__(self, llm_service: LLMService):
        self._llm = llm_service

    async def score_post(self, request: ScoreRequest) -> ScoreResponse:
        tone_section = ""
        if request.top_posts_sample:
            samples = "\n".join(f'  "{h}"' for h in request.top_posts_sample[:3])
            tone_section = f"\nTop performing posts from this user (use for tone calibration):\n{samples}"

        user_prompt = f"""Score this LinkedIn draft post:

---
{request.draft_text}
---
{tone_section}"""

        logger.info("virality_score_requested", user_id=request.user_id, post_id=request.post_id)

        result = await self._llm.generate_structured_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=1500,
            temperature=0.4,  # Lower temp for more consistent scoring
            response_schema=ScoreResponse,
        )

        breakdown_raw = result.get("breakdown", {})
        breakdown = ScoreBreakdown(
            hook_strength=int(breakdown_raw.get("hook_strength", 0)),
            readability=int(breakdown_raw.get("readability", 0)),
            value_density=int(breakdown_raw.get("value_density", 0)),
            cta_quality=int(breakdown_raw.get("cta_quality", 0)),
        )

        alternatives = [
            HookAlternative(
                hook=a.get("hook", ""),
                predicted_score=int(a.get("predicted_score", 0)),
            )
            for a in result.get("hook_alternatives", [])[:3]
        ]

        total = int(result.get("total_score", sum([
            breakdown.hook_strength, breakdown.readability,
            breakdown.value_density, breakdown.cta_quality
        ])))

        response = ScoreResponse(
            total_score=total,
            breakdown=breakdown,
            hook_alternatives=alternatives,
            reasoning=result.get("reasoning", ""),
        )

        logger.info(
            "virality_score_complete",
            user_id=request.user_id,
            post_id=request.post_id,
            total_score=total,
        )

        return response
