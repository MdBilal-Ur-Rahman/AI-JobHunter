from pydantic import BaseModel, Field
from typing import List


class NormalizedJob(BaseModel):
    is_individual_job: bool = False

    title: str = "Not specified"
    company: str = "Not specified"
    location: str = "Not specified"
    employment_type: str = "Not specified"
    experience_required: str = "Not specified"

    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)

    education: str = "Not specified"
    salary: str = "Not specified"
    application_url: str = "Not specified"
class StoredJob(BaseModel):
    user_id: str

    title: str = "Not specified"
    company: str = "Not specified"
    location: str = "Not specified"
    employment_type: str = "Not specified"
    experience_required: str = "Not specified"

    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)

    education: str = "Not specified"
    salary: str = "Not specified"
    application_url: str = "Not specified"
    source: str = "tavily"
    source_search_result_id: str = ""