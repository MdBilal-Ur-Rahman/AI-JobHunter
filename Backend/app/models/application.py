from pydantic import BaseModel
from typing import Optional


class Application(BaseModel):
    user_id: str
    job_id: str
    resume_id: str

    status: str = "saved"

    application_url: str = "Not specified"

    applied_at: Optional[str] = None

    notes: str = ""


class ApplicationPreparation(BaseModel):
    job_id: str
    resume_id: str

    cover_letter: str = ""

    application_answers: dict = {}

    notes: str = ""

    requires_user_review: bool = True
    approved: bool = False