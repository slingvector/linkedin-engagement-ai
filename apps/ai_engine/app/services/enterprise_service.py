import os
from litellm import acompletion
from app.schemas.enterprise_schemas import SignalMappingResponse, MultiTouchSequenceResponse

class EnterpriseAIService:
    def __init__(self):
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        
    async def map_signal(self, company_name: str, signal_type: str, signal_description: str) -> SignalMappingResponse:
        try:
            with open("app/prompts/system_signal_mapper.txt", "r") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "Deduce pain point from signal."
            
        user_message = f"Company: {company_name}\nSignal: {signal_type}\nDescription: {signal_description}"
        
        response = await acompletion(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format=SignalMappingResponse
        )
        
        return SignalMappingResponse.model_validate_json(response.choices[0].message.content)
        
    async def generate_sequence(self, company_name: str, target_persona: str, pain_point: str, company_context: str) -> MultiTouchSequenceResponse:
        try:
            with open("app/prompts/system_sequence_generator.txt", "r") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "Write 3 step outbound sequence."
            
        user_message = f"Company: {company_name}\nTarget: {target_persona}\nPain Point: {pain_point}\nOur Solution: {company_context}"
        
        response = await acompletion(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format=MultiTouchSequenceResponse
        )
        
        return MultiTouchSequenceResponse.model_validate_json(response.choices[0].message.content)
