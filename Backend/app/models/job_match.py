from pydantic import BaseModel, Field
from typing import List


class JobMatchResult(BaseModel):
    match_score: int = Field(
        default=0,
        ge=0,
        le=100
    )

    matched_skills: List[str] = Field(
        default_factory=list
    )

    missing_required_skills: List[str] = Field(
        default_factory=list
    )

    matched_preferred_skills: List[str] = Field(
        default_factory=list
    )

    experience_match: bool = False

    location_match: bool = False

    strengths: List[str] = Field(
        default_factory=list
    )

    gaps: List[str] = Field(
        default_factory=list
    )

    summary: str = "Not specified"