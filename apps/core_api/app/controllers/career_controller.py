from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException, Body
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.models.career import Job, Application
from app.services.career_service import CareerService

logger = structlog.get_logger()

router = APIRouter(
    prefix="/api/v1/career",
    tags=["career"],
    dependencies=[Depends(get_current_user)],
)

@router.get("/jobs", status_code=status.HTTP_200_OK)
async def get_jobs(
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Fetch a list of available jobs from the platform's intelligent ingestion engine.
    In real life this would filter by the user's career embeddings.
    """
    result = await db.execute(
        select(Job).order_by(Job.posted_at.desc()).offset(offset).limit(limit)
    )
    jobs = result.scalars().all()
    
    return {
        "jobs": [
            {
                "id": str(job.id),
                "company_name": job.company_name,
                "role_title": job.role_title,
                "description": job.description,
                "location": job.location,
                "salary_range": job.salary_range,
                "job_url": job.job_url,
                "match_score": job.match_score,
                "posted_at": job.posted_at.isoformat(),
            }
            for job in jobs
        ]
    }


def get_career_service(db: AsyncSession = Depends(get_db)) -> CareerService:
    return CareerService(db)


@router.post("/upload-resume", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: CareerService = Depends(get_career_service)
):
    """
    Accepts a PDF resume, parses its text, and stores it in the database.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    # Read the entire file into memory (since resumes are generally <1MB)
    file_bytes = await file.read()
    
    try:
        resume = await service.parse_and_store_resume(
            user_id=current_user.id,
            file_name=file.filename or "resume.pdf",
            file_bytes=file_bytes
        )
        return {"resume_id": str(resume.id), "message": "Resume successfully parsed and safely stored."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/applications/{id}/status", status_code=status.HTTP_200_OK)
async def update_application_status(
    id: str,
    status_val: str = Body(..., embed=True, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates the CRM pipeline state of an Application (e.g., 'saved' -> 'applied').
    """
    valid_statuses = ["saved", "applied", "interviewing", "rejected"]
    if status_val not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status string.")
        
    result = await db.execute(
        select(Application).where(Application.id == id, Application.user_id == current_user.id)
    )
    application = result.scalars().first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found or unauthorized.")
        
    application.status = status_val
    await db.commit()
    
    return {"message": "Status updated successfully.", "application_id": id, "new_status": status_val}
