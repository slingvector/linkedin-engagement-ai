import json
import os
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
import litellm
import aiofiles

router = APIRouter(prefix="/webhooks/evals", tags=["llmops_evals"])

api_key_header = APIKeyHeader(name="X-AI-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != os.environ.get("AI_ENGINE_API_KEY", "dev-secret-key"):
        raise HTTPException(status_code=403, detail="Could not validate API key")
    return api_key

class EvaluationRequest(BaseModel):
    action_type: str
    ai_draft: str
    human_final: str
    distance_score: float

class EvaluationResponse(BaseModel):
    hallucination_score: int = Field(..., ge=0, le=100)
    tone_adherence_score: int = Field(..., ge=0, le=100)
    safety_compliance_score: int = Field(..., ge=0, le=100)
    judge_rationale: str

@router.post("/score-generation", response_model=EvaluationResponse)
async def score_generation(
    req: EvaluationRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    LLM-as-a-Judge evaluator grading the AI draft against the human's final edit.
    """
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "system_llm_judge.txt")
    try:
        async with aiofiles.open(prompt_path, "r") as f:
            system_prompt = await f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load system prompt: {e}")

    user_payload = (
        f"Action Type: {req.action_type}\n"
        f"AI Draft: {req.ai_draft}\n"
        f"Human Final Edit: {req.human_final}\n"
        f"Distance Score: {req.distance_score}\n"
    )

    try:
        response = await litellm.acompletion(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload}
            ],
            response_format={"type": "json_object"},
            temperature=0.0 # Deterministic grading
        )
        
        content = response.choices[0].message.content
        result = json.loads(content)
        
        return EvaluationResponse(
            hallucination_score=result.get("hallucination_score", 95),
            tone_adherence_score=result.get("tone_adherence_score", 95),
            safety_compliance_score=result.get("safety_compliance_score", 100),
            judge_rationale=result.get("judge_rationale", "Evaluation successful")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM scoring failed: {e}")
