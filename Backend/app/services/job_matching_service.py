import json
import re

from app.models.job_match import JobMatchResult
from app.services.gemini_service import generate_text


# =========================================================
# JOB MATCHING PROMPT
# =========================================================

def build_job_matching_prompt(
    resume_text: str,
    job_title: str,
    company: str,
    location: str,
    experience_required: str,
    required_skills: list[str],
    preferred_skills: list[str]
) -> str:

    required_skills_text = ", ".join(
        required_skills
    ) if required_skills else "Not specified"

    preferred_skills_text = ", ".join(
        preferred_skills
    ) if preferred_skills else "Not specified"

    return f"""
You are a job matching assistant.

Your task is to compare the supplied resume with the supplied job.

IMPORTANT RULES:

1. Use ONLY information explicitly present in the resume and job data.
2. Do NOT invent skills, experience, education, projects, or achievements.
3. Do NOT assume a skill exists just because another similar skill exists.
4. Required skills and preferred skills must be treated separately.
5. Missing required skills must contain only skills that are explicitly required by the job but are not explicitly present in the resume.
6. matched_skills must contain only required skills explicitly present in the resume.
7. matched_preferred_skills must contain only preferred skills explicitly present in the resume.
8. experience_match should be true only when the resume provides enough explicit information to support the required experience.
9. location_match should be true only when the resume location and job location clearly match.
10. If information is unavailable, do not guess. Use false or an empty list where appropriate.
11. match_score must be an integer from 0 to 100.
12. Return ONLY valid JSON.
13. Do NOT include markdown code fences.
14. Do NOT include additional text outside the JSON.

JOB INFORMATION:

Title:
{job_title}

Company:
{company}

Location:
{location}

Experience Required:
{experience_required}

Required Skills:
{required_skills_text}

Preferred Skills:
{preferred_skills_text}


RESUME:

{resume_text}


Return JSON using exactly this structure:

{{
    "match_score": 0,
    "matched_skills": [],
    "missing_required_skills": [],
    "matched_preferred_skills": [],
    "experience_match": false,
    "location_match": false,
    "strengths": [],
    "gaps": [],
    "summary": "Not specified"
}}
"""


# =========================================================
# JSON EXTRACTION
# =========================================================

def extract_json_from_response(
    response: str
) -> dict:

    response = response.strip()

    # ---------------------------------------------------------
    # REMOVE MARKDOWN CODE FENCES IF GEMINI RETURNS THEM
    # ---------------------------------------------------------

    response = re.sub(
        r"^```json\s*",
        "",
        response,
        flags=re.IGNORECASE
    )

    response = re.sub(
        r"^```\s*",
        "",
        response
    )

    response = re.sub(
        r"\s*```$",
        "",
        response
    )

    response = response.strip()

    # ---------------------------------------------------------
    # DIRECT JSON PARSE
    # ---------------------------------------------------------

    try:

        return json.loads(
            response
        )

    except json.JSONDecodeError:

        pass

    # ---------------------------------------------------------
    # TRY TO FIND JSON OBJECT
    # ---------------------------------------------------------

    start_index = response.find("{")
    end_index = response.rfind("}")

    if (
        start_index == -1
        or end_index == -1
        or end_index <= start_index
    ):

        raise ValueError(
            "Gemini did not return valid JSON"
        )

    json_text = response[
        start_index:end_index + 1
    ]

    try:

        return json.loads(
            json_text
        )

    except json.JSONDecodeError as e:

        raise ValueError(
            "Gemini returned invalid JSON"
        ) from e


# =========================================================
# VALIDATE MATCH RESULT
# =========================================================

def validate_match_result(
    data: dict
) -> JobMatchResult:

    try:

        result = JobMatchResult(
            **data
        )

    except Exception as e:

        raise ValueError(
            "Gemini returned invalid job match data"
        ) from e

    return result


# =========================================================
# JOB MATCHING
# =========================================================

def match_resume_with_job(
    resume_text: str,
    job_title: str,
    company: str,
    location: str,
    experience_required: str,
    required_skills: list[str],
    preferred_skills: list[str]
) -> JobMatchResult:

    # ---------------------------------------------------------
    # VALIDATE RESUME
    # ---------------------------------------------------------

    if not resume_text.strip():

        raise ValueError(
            "Resume text cannot be empty"
        )

    # ---------------------------------------------------------
    # BUILD PROMPT
    # ---------------------------------------------------------

    prompt = build_job_matching_prompt(
        resume_text=resume_text,
        job_title=job_title,
        company=company,
        location=location,
        experience_required=experience_required,
        required_skills=required_skills,
        preferred_skills=preferred_skills
    )

    # ---------------------------------------------------------
    # CALL GEMINI
    # ---------------------------------------------------------

    response = generate_text(
        prompt
    )

    # ---------------------------------------------------------
    # PARSE JSON
    # ---------------------------------------------------------

    data = extract_json_from_response(
        response
    )

    # ---------------------------------------------------------
    # VALIDATE STRUCTURE
    # ---------------------------------------------------------

    result = validate_match_result(
        data
    )

    return result