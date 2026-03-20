import os
from litellm import acompletion
from app.schemas.talent_schemas import CandidateScoringResponse, OutreachDraftResponse

class TalentAIService:
    def __init__(self):
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        
    async def score_candidate(self, candidate_profile: str, requisition_description: str) -> CandidateScoringResponse:
        try:
            with open("app/prompts/system_candidate_scorer.txt", "r") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "Evaluate candidate fit 0-100 against JD."
            
        user_message = f"Candidate:\n{candidate_profile}\n\nRequisition:\n{requisition_description}"
        
        response = await acompletion(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format=CandidateScoringResponse
        )
        
        result_json = response.choices[0].message.content
        return CandidateScoringResponse.model_validate_json(result_json)
        
    async def draft_outreach(self, candidate_profile: str, requisition_description: str, company_context: str) -> OutreachDraftResponse:
        try:
            with open("app/prompts/system_sourcing_copilot.txt", "r") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "Write 1 subject and 2 highly personalized InMails based on candidate gaps/growth."
            
        user_message = f"Profile:\n{candidate_profile}\n\nRequisition:\n{requisition_description}\n\nCompany Context: {company_context}"
        
        response = await acompletion(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format=OutreachDraftResponse
        )
        
        result_json = response.choices[0].message.content
        return OutreachDraftResponse.model_validate_json(result_json)
