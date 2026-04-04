import asyncio
import json
import random
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import _async_session as AsyncSessionLocal
from app.models.base import Base
from app.models.user import User
from app.models.llmops import ShadowActionLog, LLMEvaluation

logger = logging.getLogger(__name__)

MOCK_INPUTS = [
    {
        "type": "post_generation",
        "ai": "I'm thrilled to announce my new startup!",
        "human": "I am excited to share that I am building a new startup focused on AI infrastructure.",
        "sim": 0.65
    },
    {
        "type": "dm_draft",
        "ai": "Hi John, do you want to buy my software?",
        "human": "Hey John, noticed you're scaling the engineering team. Are you facing any bottlenecks with deployments?",
        "sim": 0.10
    },
    {
        "type": "comment_reply",
        "ai": "Great point! I totally agree with you.",
        "human": "Great point! I totally agree with you.",
        "sim": 1.0
    },
    {
        "type": "sequence_generation",
        "ai": "Saw you raised Series A. Let's chat.",
        "human": "Saw recent news about your Series A—congrats! Expanding the architecture team must be top of mind.",
        "sim": 0.40
    }
]

async def seed_evals_loop():
    """
    Simulates a background process running LLM-as-a-Judge Evals and ingesting telemetry logs.
    """
    logger.info("Starting LLMOps & Evaluation Telemetry Background Worker...")
    
    while True:
        try:
            await asyncio.sleep(20) # Fast polling for UI data population
            async with AsyncSessionLocal() as session:
                # 1. Automate Comment Strategy Generation for newly ingested posts
                from app.repositories.creator_repository import CreatorRepository
                from app.repositories.comment_repository import CommentDraftRepository
                from app.services.creator_service import CreatorService
                from app.models.creator import IngestedPost
                from app.schemas.creator import CommentGenerateRequest

                service = CreatorService(CreatorRepository(session), CommentDraftRepository(session))
                unprocessed = await session.execute(
                    select(IngestedPost).where(IngestedPost.is_processed == 0).limit(5)
                )
                for post in unprocessed.scalars().all():
                    # Find the user for this post (admin for this demo)
                    res = await session.execute(select(User).limit(1))
                    user = res.scalar_one_or_none()
                    if user:
                        try:
                            await service.generate_comments(user.id, CommentGenerateRequest(ingested_post_id=post.id))
                            logger.info(f"AI: Generated strategies for post {post.id}")
                        except Exception as e:
                            logger.error(f"AI: Failed to generate for post {post.id}: {e}")

                # 2. Keep the Shadow Action & Telemetry simulation (optional, but keeps logs active)
                res = await session.execute(select(User).limit(1))
                user = res.scalar_one_or_none()
                
                if user:
                    mock_act = random.choice(MOCK_INPUTS)
                    
                    # 1. Log the Shadow Action
                    shadow_log = ShadowActionLog(
                        user_id=user.id,
                        action_type=mock_act["type"],
                        ai_draft_content=mock_act["ai"],
                        human_final_content=mock_act["human"],
                        edit_similarity_score=mock_act["sim"]
                    )
                    session.add(shadow_log)
                    await session.commit()
                    await session.refresh(shadow_log)
                    
                    # 2. Simulate the LLM-as-a-Judge evaluating that generation
                    val_variance = random.randint(-5, 0)
                    eval_log = LLMEvaluation(
                        log_id=shadow_log.id,
                        hallucination_score=100 + val_variance if mock_act["sim"] > 0.5 else 85 + val_variance,
                        tone_adherence_score=95 + val_variance,
                        safety_compliance_score=100,
                        judge_rationale="The AI output was contextually safe and generally adhered to the required structure, though minor tone adjustments were injected by the human."
                    )
                    session.add(eval_log)
                    await session.commit()
                    logger.info(f"LLMOps: Telemetry generated & evaluated for action type {mock_act['type']}")

        except Exception as e:
            logger.error(f"LLMOps Seeder encountered error: {e}")
            await asyncio.sleep(5)
