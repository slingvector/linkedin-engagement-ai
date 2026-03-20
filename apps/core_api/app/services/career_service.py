import io
import pdfplumber
import structlog
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.career import Resume, Application
from app.config import get_settings

logger = structlog.get_logger()

class CareerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def parse_and_store_resume(self, user_id: UUID, file_name: str, file_bytes: bytes) -> Resume:
        """
        Parses raw PDF bytes into a single raw text string via pdfplumber.
        Stores the resulting text in the `resumes` table.
        """
        raw_text = ""
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        raw_text += text + "\n"
        except Exception as e:
            logger.error("pdf_parsing_failed", error=str(e), file_name=file_name)
            raise ValueError(f"Failed to parse PDF: {str(e)}")
            
        if not raw_text.strip():
            raise ValueError("No extractable text found in PDF. Make sure it's not an image-only scan.")
            
        resume = Resume(
            user_id=user_id,
            file_name=file_name,
            raw_text=raw_text.strip()
        )
        self.db.add(resume)
        await self.db.commit()
        await self.db.refresh(resume)
        
        logger.info("resume_parsed_and_stored", resume_id=str(resume.id))
        return resume
