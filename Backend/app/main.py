from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    UploadFile,
    File
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from fastapi.middleware.cors import CORSMiddleware

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from dotenv import load_dotenv

import os

from pydantic import BaseModel

from typing import List

from bson import ObjectId
from bson.errors import InvalidId

from jose import JWTError, jwt

from datetime import (
    datetime,
    timedelta,
    timezone
)

from uuid import uuid4
import logging

from tavily import TavilyClient


# =========================================================
# SERVICES
# =========================================================

from app.services.job_normalization_service import normalize_job

from app.services.resume_text_service import extract_resume_text

from app.services.resume_verification_service import verify_resume_text

from app.services.resume_tailoring_service import tailor_resume

from app.services.job_matching_service import match_resume_with_job

from app.services.playwright_service import (
    open_application_page_for_user,
    inspect_application_page
)

from app.services.application_field_mapping_service import (
    map_application_fields
)

from app.services.url_verification_service import (
    verify_application_url
)

from app.services.tavily_job_search_service import (
    _is_listing_page,
    _is_non_job_resource,
    _matches_requested_criteria,
    search_and_store_jobs
)

from app.services.application_submission_gate_service import (
    check_submission_gate
)

from app.services.password_reset_service import (
    PasswordResetDeliveryError,
    build_password_reset_url,
    create_password_reset_token,
    get_password_reset_mail_settings,
    hash_password_reset_token,
    send_password_reset_email,
)

from app.services.password_service import (
    MAX_BCRYPT_PASSWORD_BYTES,
    hash_password,
    password_within_bcrypt_limit,
    verify_password,
)


# =========================================================
# MODELS
# =========================================================

from app.models.job import StoredJob

from app.models.application import (
    Application,
    ApplicationPreparation
)


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

logger = logging.getLogger(__name__)


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="AI JobHunter API",
    description="AI-powered job discovery and application assistant",
    version="1.0.0",
    swagger_ui_parameters={
        "persistAuthorization": True
    }
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


# =========================================================
# CORS
# =========================================================

cors_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

if not cors_origins or "*" in cors_origins:
    raise RuntimeError(
        "FRONTEND_ORIGINS must contain explicit frontend origins"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# JWT SETTINGS
# =========================================================

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not configured in environment variables"
    )

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()


# =========================================================
# MONGODB
# =========================================================

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError(
        "MONGO_URI is not configured in environment variables"
    )

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not TAVILY_API_KEY:
    raise RuntimeError(
        "TAVILY_API_KEY is not configured"
    )


client = MongoClient(MONGO_URI)

db = client["ai-jobhunter"]

tavily_client = TavilyClient(
    api_key=TAVILY_API_KEY
)


# =========================================================
# DATABASE COLLECTIONS
# =========================================================

users_collection = db["users"]

job_search_results_collection = db["job_search_results"]

jobs_collection = db["jobs"]

job_matches_collection = db["job_matches"]

applications_collection = db["applications"]

resumes_collection = db["resumes"]

preferences_collection = db["preferences"]

revoked_tokens_collection = db["revoked_tokens"]

active_sessions_collection = db["active_sessions"]

password_reset_tokens_collection = db["password_reset_tokens"]


# =========================================================
# DATABASE INDEXES
# =========================================================

# ---------------------------------------------------------
# USERS
# ---------------------------------------------------------

users_collection.create_index(
    "email",
    unique=True
)


# ---------------------------------------------------------
# JOBS
# ---------------------------------------------------------

jobs_collection.create_index(
    [
        ("user_id", 1),
        ("source_search_result_id", 1)
    ],
    unique=True,
    partialFilterExpression={
        "source_search_result_id": {
            "$exists": True
        }
    }
)


jobs_collection.create_index(
    [
        ("user_id", 1),
        ("created_at", -1)
    ]
)


# ---------------------------------------------------------
# JOB MATCHES
# ---------------------------------------------------------

job_matches_collection.create_index(
    [
        ("user_id", 1),
        ("job_id", 1),
        ("resume_id", 1)
    ],
    unique=True
)


job_matches_collection.create_index(
    [
        ("user_id", 1),
        ("created_at", -1)
    ]
)


# ---------------------------------------------------------
# APPLICATIONS
# ---------------------------------------------------------
# Same user + same job + same resume
# must not create duplicate applications.
#
# Existing MongoDB index is checked by its KEY pattern,
# not by its name.
# ---------------------------------------------------------

APPLICATION_INDEX_KEYS = [
    ("user_id", 1),
    ("job_id", 1),
    ("resume_id", 1)
]

existing_application_indexes = (
    applications_collection.index_information()
)

application_unique_index_exists = False

for index_name, index_info in existing_application_indexes.items():

    if index_name == "_id_":
        continue

    existing_keys = list(
        index_info.get("key", [])
    )

    if existing_keys == APPLICATION_INDEX_KEYS:

        if index_info.get("unique", False):
            application_unique_index_exists = True

        else:
            applications_collection.drop_index(
                index_name
            )


if not application_unique_index_exists:

    applications_collection.create_index(
        APPLICATION_INDEX_KEYS,
        unique=True
    )


applications_collection.create_index(
    [
        ("user_id", 1),
        ("created_at", -1)
    ]
)


# ---------------------------------------------------------
# RESUMES
# ---------------------------------------------------------

resumes_collection.create_index(
    [
        ("user_id", 1),
        ("created_at", -1)
    ]
)


# ---------------------------------------------------------
# PREFERENCES
# ---------------------------------------------------------

preferences_collection.create_index(
    "user_id",
    unique=True
)


# ---------------------------------------------------------
# REVOKED TOKENS
# ---------------------------------------------------------

revoked_tokens_collection.create_index(
    "jti",
    unique=True
)


revoked_tokens_collection.create_index(
    "expires_at",
    expireAfterSeconds=0
)


# ---------------------------------------------------------
# ACTIVE SESSIONS
# ---------------------------------------------------------

active_sessions_collection.create_index(
    "user_id",
    unique=True
)


active_sessions_collection.create_index(
    "jti",
    unique=True
)

password_reset_tokens_collection.create_index(
    "token_hash",
    unique=True
)

password_reset_tokens_collection.create_index(
    "expires_at",
    expireAfterSeconds=0
)

password_reset_tokens_collection.create_index(
    [
        ("user_id", 1),
        ("created_at", -1)
    ]
)


# =========================================================
# LIMITS
# =========================================================

MAX_RESUME_SIZE = 5 * 1024 * 1024

ALLOWED_RESUME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}

MAX_JOB_SEARCH_RESULTS_PER_USER = 100

MAX_JOB_CONTENT_LENGTH = 100_000

MAX_RESUMES_PER_USER = 3

MAX_JOBS_PER_USER = 100

MAX_APPLICATIONS_PER_USER = 100


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_user_id(current_user: dict) -> str:
    return str(current_user["_id"])


def ensure_application_is_individual_job(application: dict) -> None:
    application_url = application.get("application_url", "")
    if (
        _is_listing_page("", application_url)
        or _is_non_job_resource("", application_url)
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "This application points to a profile, company, or "
                "job-search page, not an individual job posting."
            ),
        )


def is_valid_object_id(value: str) -> bool:
    return ObjectId.is_valid(value)


def serialize_object_id(value):
    if isinstance(value, ObjectId):
        return str(value)

    return value


# =========================================================
# JWT TOKEN CREATION
# =========================================================

def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None
):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=15)
    )

    to_encode.update({
        "exp": expire,
        "jti": str(uuid4())
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# =========================================================
# CURRENT USER
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")
        jti = payload.get("jti")

        if not user_id or not jti:
            raise HTTPException(
                status_code=401,
                detail="Token is missing user ID or session ID. Please login again."
            )

        try:
            object_user_id = ObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=401,
                detail="Invalid user ID in token. Please login again."
            )

        revoked_token = revoked_tokens_collection.find_one({
            "jti": jti
        })

        if revoked_token:
            raise HTTPException(
                status_code=401,
                detail="Token has been revoked. Please login again."
            )

        active_session = active_sessions_collection.find_one({
            "user_id": user_id,
            "jti": jti
        })

        if not active_session:
            raise HTTPException(
                status_code=401,
                detail="Active login session not found. Please login again."
            )

        session_expires_at = active_session.get("expires_at")

        if session_expires_at:
            if session_expires_at.tzinfo is None:
                session_expires_at = session_expires_at.replace(
                    tzinfo=timezone.utc
                )

            if session_expires_at <= datetime.now(timezone.utc):
                active_sessions_collection.delete_one({
                    "_id": active_session["_id"]
                })

                raise HTTPException(
                    status_code=401,
                    detail="Login session has expired. Please login again."
                )

        user = users_collection.find_one({
            "_id": object_user_id
        })

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="User account not found. Please login again."
            )

        return user

    except HTTPException:
        raise

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token. Please login again."
        )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed. Please login again."
        )



# =========================================================
# PYDANTIC MODELS
# =========================================================

class Job(BaseModel):
    title: str
    company: str
    location: str
    skills: List[str]
    experience: str


class User(BaseModel):
    name: str
    email: str
    password: str


class LoginUser(BaseModel):
    email: str
    password: str


class ProfileUpdate(BaseModel):
    name: str
    email: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UserPreferences(BaseModel):
    job_titles: List[str]
    locations: List[str]
    skills: List[str]
    min_experience: str
    work_mode: str
    employment_type: str


class JobAgentRequest(BaseModel):
    message: str


# =========================================================
# JOBS - CREATE
# =========================================================

@app.post("/jobs")
def create_job(
    job: Job,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    current_job_count = jobs_collection.count_documents({
        "user_id": user_id
    })

    if current_job_count >= MAX_JOBS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail="Maximum saved jobs limit reached"
        )

    job_data = job.model_dump()

    job_data["user_id"] = user_id

    now = datetime.now(timezone.utc)

    job_data["created_at"] = now
    job_data["updated_at"] = now

    result = jobs_collection.insert_one(
        job_data
    )

    return {
        "message": "Job created successfully",
        "job_id": str(result.inserted_id)
    }


# =========================================================
# JOBS - MY JOBS
# =========================================================

@app.get("/users/my-jobs")
def get_my_jobs(
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    jobs = list(
        jobs_collection.find({
            "user_id": user_id
        }).sort(
            "created_at",
            -1
        )
    )

    for job in jobs:
        job["_id"] = str(job["_id"])

    return jobs


# =========================================================
# JOBS - MY STORED NORMALIZED JOBS
# =========================================================
@app.get("/users/my-stored-jobs")
def get_my_stored_jobs(
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    stored_jobs = list(
        jobs_collection.find({
            "user_id": user_id
        }).sort("created_at", -1)
    )

    jobs = []

    for job in stored_jobs:
        job_url = job.get("application_url", "")

        if (
            _is_listing_page(job.get("title", ""), job_url)
            or _is_non_job_resource(job.get("title", ""), job_url)
        ):
            continue

        jobs.append({
            "job_id": str(job["_id"]),
            "title": job.get("title", "Not specified"),
            "company": job.get("company", "Not specified"),
            "location": job.get("location", "Not specified"),
            "employment_type": job.get(
                "employment_type", "Not specified"
            ),
            "experience_required": job.get(
                "experience_required", "Not specified"
            ),
            "required_skills": job.get("required_skills", []),
            "preferred_skills": job.get("preferred_skills", []),
            "education": job.get("education", "Not specified"),
            "salary": job.get("salary", "Not specified"),
            "application_url": job.get(
                "application_url", "Not specified"
            ),
            "source": job.get("source", "Not specified"),
            "source_search_result_id": job.get(
                "source_search_result_id", ""
            ),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at")
        })

    return {
        "message": "Stored jobs fetched successfully",
        "total_jobs": len(jobs),
        "jobs": jobs
    }
@app.get("/debug/jobhunter-counts")
def debug_jobhunter_counts(
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    return {
        "user_id": user_id,
        "raw_search_results": job_search_results_collection.count_documents({
            "user_id": user_id
        }),
        "normalized_jobs": jobs_collection.count_documents({
            "user_id": user_id
        }),
        "job_matches": job_matches_collection.count_documents({
            "user_id": user_id
        }),
        "applications": applications_collection.count_documents({
            "user_id": user_id
        })
    }
# =========================================================
# JOBS - SEARCH
# =========================================================

@app.get("/jobs/search")
def search_jobs(
    current_user: dict = Depends(get_current_user),
    location: str | None = None,
    skill: str | None = None
):
    query = {
        "user_id": get_user_id(current_user)
    }

    if location:
        query["location"] = {
            "$regex": location,
            "$options": "i"
        }

    if skill:
        query["skills"] = {
            "$regex": skill,
            "$options": "i"
        }

    jobs = list(
        jobs_collection.find(query)
    )

    for job in jobs:
        job["_id"] = str(job["_id"])

    return jobs


# =========================================================
# TAVILY SEARCH RESULTS - GET MY SAVED RESULTS
# =========================================================

def _is_visible_search_result(result: dict) -> bool:
    title = result.get("title", "")
    url = result.get("url", "")
    if _is_listing_page(title, url) or _is_non_job_resource(title, url):
        return False

    job_title_query = result.get("job_title_query")
    location_query = result.get("location_query")
    if job_title_query == "custom" or location_query == "custom":
        return False

    return _matches_requested_criteria(
        title=title,
        content=result.get("content", ""),
        location=result.get("location"),
        job_title_query=job_title_query,
        location_query=location_query,
    )


@app.get("/jobs/search-results")
def get_my_search_results(
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    results = list(
        job_search_results_collection.find({
            "user_id": user_id
        }).sort(
            "created_at",
            -1
        )
    )

    results = [result for result in results if _is_visible_search_result(result)]

    for result in results:
        result["_id"] = str(result["_id"])

    return {
        "total_results": len(results),
        "results": results
    }


# =========================================================
# JOBS - NORMALIZE AND STORE
# =========================================================

@app.post("/jobs/normalize-and-store")
def normalize_and_store_job(
    search_result_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(search_result_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid search result ID"
        )

    search_result = job_search_results_collection.find_one({
        "_id": ObjectId(search_result_id),
        "user_id": user_id
    })

    if not search_result:
        raise HTTPException(
            status_code=404,
            detail="Search result not found"
        )

    job_title = search_result.get(
        "title"
    ) or "Not specified"

    job_url = search_result.get(
        "url"
    ) or ""

    if _is_listing_page(job_title, job_url):
        return {
            "message": (
                "This is a job-search results page, not an individual "
                "job posting. Open the result and save a specific job."
            ),
            "search_result_id": search_result_id,
            "is_individual_job": False,
            "stored": False
        }

    if _is_non_job_resource(job_title, job_url):
        return {
            "message": (
                "This link is a company review or informational page, "
                "not a job posting, so it was not saved."
            ),
            "search_result_id": search_result_id,
            "is_individual_job": False,
            "stored": False
        }

    existing_job = jobs_collection.find_one({
        "user_id": user_id,
        "source_search_result_id": search_result_id
    })

    if existing_job:
        return {
            "message": "Job already normalized and stored",
            "job_id": str(existing_job["_id"]),
            "search_result_id": search_result_id,
            "is_individual_job": True
        }

    current_job_count = jobs_collection.count_documents({
        "user_id": user_id
    })

    if current_job_count >= MAX_JOBS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail="Maximum saved jobs limit reached"
        )

    try:
        verification_result = verify_application_url(
            job_url
        )

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Application URL verification failed: {str(error)}"
        )

    if not verification_result.get("valid", False):
        return {
            "message": (
                "This job URL could not be verified against a recognized "
                "job-site domain, so it was not saved."
            ),
            "search_result_id": search_result_id,
            "stored": False,
            "url_verified": False
        }

    now = datetime.now(timezone.utc)

    stored_job = StoredJob(
        user_id=user_id,
        title=job_title,
        company=search_result.get("company") or "Not specified",
        location=search_result.get("location") or "Not specified",
        employment_type=(
            search_result.get("employment_type") or "Not specified"
        ),
        experience_required=(
            search_result.get("experience_required") or "Not specified"
        ),
        salary=search_result.get("salary") or "Not specified",
        application_url=job_url,
        source="tavily",
        source_search_result_id=search_result_id
    )

    stored_job_data = stored_job.model_dump()

    stored_job_data["application_url_verified"] = True
    stored_job_data["application_url_verification"] = verification_result
    stored_job_data["created_at"] = now
    stored_job_data["updated_at"] = now

    try:
        insert_result = jobs_collection.insert_one(
            stored_job_data
        )

    except DuplicateKeyError:
        existing_job = jobs_collection.find_one({
            "user_id": user_id,
            "source_search_result_id": search_result_id
        })

        if existing_job:
            return {
                "message": "Job already normalized and stored",
                "job_id": str(existing_job["_id"]),
                "search_result_id": search_result_id,
                "is_individual_job": True
            }

        raise HTTPException(
            status_code=409,
            detail="Job already exists"
        )

    return {
        "message": (
            "Job posting saved. Employer and job details still need "
            "your review."
        ),

        "job_id": str(
            insert_result.inserted_id
        ),

        "search_result_id": search_result_id,

        "is_individual_job": True,

        "url_verified": True,
        "stored": True,

        "job": stored_job.model_dump()
    }


# =========================================================
# JOBS - GET ALL
# =========================================================

@app.get("/jobs")
def get_jobs(
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    jobs = list(
        jobs_collection.find({
            "user_id": user_id
        }).sort(
            "created_at",
            -1
        )
    )

    formatted_jobs = []

    for job in jobs:
        formatted_jobs.append({
            "job_id": str(job["_id"]),

            "title": job.get(
                "title",
                "Not specified"
            ),

            "company": job.get(
                "company",
                "Not specified"
            ),

            "location": job.get(
                "location",
                "Not specified"
            ),

            "employment_type": job.get(
                "employment_type",
                "Not specified"
            ),

            "experience_required": job.get(
                "experience_required",
                "Not specified"
            ),

            "required_skills": job.get(
                "required_skills",
                []
            ),

            "preferred_skills": job.get(
                "preferred_skills",
                []
            ),

            "education": job.get(
                "education",
                "Not specified"
            ),

            "salary": job.get(
                "salary",
                "Not specified"
            ),

            "application_url": job.get(
                "application_url",
                "Not specified"
            ),

            "source": job.get(
                "source",
                "tavily"
            ),

            "source_search_result_id": job.get(
                "source_search_result_id",
                ""
            ),

            "created_at": job.get(
                "created_at"
            ),

            "updated_at": job.get(
                "updated_at"
            )
        })

    return {
        "message": "Jobs fetched successfully",
        "total_jobs": len(formatted_jobs),
        "jobs": formatted_jobs
    }


# =========================================================
# JOBS - NORMALIZE AND STORE BY ID
# =========================================================

@app.get("/jobs/normalize-and-store/{search_result_id}")
def normalize_and_store_job_by_id(
    search_result_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(search_result_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid search result ID"
        )

    search_result = job_search_results_collection.find_one({
        "_id": ObjectId(search_result_id),
        "user_id": user_id
    })

    if not search_result:
        raise HTTPException(
            status_code=404,
            detail="Search result not found"
        )

    existing_job = jobs_collection.find_one({
        "user_id": user_id,
        "source_search_result_id": search_result_id
    })

    if existing_job:
        return {
            "message": "Job already exists",
            "job_id": str(existing_job["_id"])
        }

    current_job_count = jobs_collection.count_documents({
        "user_id": user_id
    })

    if current_job_count >= MAX_JOBS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail="Maximum saved jobs limit reached"
        )

    try:
        normalized_job = normalize_job(
            job_title=search_result.get(
                "title",
                ""
            ),
            job_url=search_result.get(
                "url",
                ""
            ),
            job_content=search_result.get(
                "content",
                ""
            )
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Job normalization failed: {str(error)}"
        )

    if not normalized_job.is_individual_job:
        return {
            "message": "Result is not an individual job posting",
            "search_result_id": search_result_id,
            "stored": False,
            "normalized_job": normalized_job.model_dump()
        }

    application_url = normalized_job.application_url

    if not application_url or application_url == "Not specified":
        return {
            "message": "Job does not have a valid application URL",
            "search_result_id": search_result_id,
            "stored": False,
            "url_verified": False,
            "normalized_job": normalized_job.model_dump()
        }

    try:
        verification_result = verify_application_url(
            application_url
        )

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Application URL verification failed: {str(error)}"
        )

    if not verification_result.get(
        "valid",
        False
    ):
        return {
            "message": "Application URL could not be verified",
            "search_result_id": search_result_id,
            "stored": False,
            "url_verified": False,
            "verification": verification_result,
            "normalized_job": normalized_job.model_dump()
        }

    now = datetime.now(timezone.utc)

    stored_job_data = {
        "user_id": user_id,

        "title": normalized_job.title,

        "company": normalized_job.company,

        "location": normalized_job.location,

        "employment_type": normalized_job.employment_type,

        "experience_required": (
            normalized_job.experience_required
        ),

        "required_skills": (
            normalized_job.required_skills
        ),

        "preferred_skills": (
            normalized_job.preferred_skills
        ),

        "education": normalized_job.education,

        "salary": normalized_job.salary,

        "application_url": application_url,

        "application_url_verified": True,

        "application_url_verification": verification_result,

        "source": "tavily",

        "source_search_result_id": search_result_id,

        "created_at": now,

        "updated_at": now
    }

    try:
        insert_result = jobs_collection.insert_one(
            stored_job_data
        )

    except DuplicateKeyError:
        existing_job = jobs_collection.find_one({
            "user_id": user_id,
            "source_search_result_id": search_result_id
        })

        if existing_job:
            return {
                "message": "Job already exists",
                "stored": False,
                "job_id": str(existing_job["_id"])
            }

        raise HTTPException(
            status_code=409,
            detail="Job already exists"
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store normalized job: {str(error)}"
        )

    return {
        "message": "Job normalized and stored successfully",

        "stored": True,

        "job_id": str(
            insert_result.inserted_id
        ),

        "search_result_id": search_result_id,

        "url_verified": True,

        "normalized_job": normalized_job.model_dump()
    }


# =========================================================
# JOBS - MATCH HISTORY
# =========================================================

@app.get("/jobs/matches")
def get_job_matches(
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    matches = job_matches_collection.find({
        "user_id": user_id
    }).sort(
        "created_at",
        -1
    )

    results = []

    for match in matches:
        results.append({
            "match_id": str(match["_id"]),

            "job_id": match.get(
                "job_id"
            ),

            "resume_id": match.get(
                "resume_id"
            ),

            "match_result": match.get(
                "match_result",
                {}
            ),

            "created_at": match.get(
                "created_at"
            ),

            "updated_at": match.get(
                "updated_at"
            )
        })

    return {
        "message": "Job match history fetched successfully",
        "total_matches": len(results),
        "matches": results
    }

# @app.get("/jobs/match/{job_id}/{resume_id}")
# @app.get("/jobs/match/{job_id}/{resume_id}")
# @app.get("/jobs/match/{job_id}/{resume_id}")
@app.get("/jobs/match/{job_id}/{resume_id}")
def match_job_with_resume(
    job_id: str,
    resume_id: str,
    current_user: dict = Depends(get_current_user),
):
    user_id = get_user_id(current_user)

    if not is_valid_object_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")

    if not is_valid_object_id(resume_id):
        raise HTTPException(status_code=400, detail="Invalid resume ID")

    job = jobs_collection.find_one({
        "_id": ObjectId(job_id),
        "user_id": user_id,
    })

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    resume = resumes_collection.find_one({
        "_id": ObjectId(resume_id),
        "user_id": user_id,
    })

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if resume.get("resume_verified") is not True:
        raise HTTPException(
            status_code=400,
            detail="Resume must be verified before matching",
        )

    resume_text = resume.get("verified_resume_text")

    if not isinstance(resume_text, str) or not resume_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Verified resume text is missing. Extract and verify the resume first.",
        )

    try:
        result = match_resume_with_job(
            resume_text=resume_text,
            job_title=job.get("title", ""),
            company=job.get("company", ""),
            location=job.get("location", ""),
            experience_required=job.get("experience_required")
            or job.get("experience", ""),
            required_skills=job.get("required_skills")
            or job.get("skills", []),
            preferred_skills=job.get("preferred_skills", []),
        )

        if hasattr(result, "model_dump"):
            match_result = result.model_dump()
        else:
            match_result = dict(result)

        now = datetime.now(timezone.utc)

        saved_match = job_matches_collection.find_one_and_update(
            {
                "user_id": user_id,
                "job_id": job_id,
                "resume_id": resume_id,
            },
            {
                "$set": {
                    "match_result": match_result,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "user_id": user_id,
                    "job_id": job_id,
                    "resume_id": resume_id,
                    "created_at": now,
                },
            },
            upsert=True,
            return_document=True,
        )

        return {
            "message": "Job matching completed successfully",
            "match_id": str(saved_match["_id"]),
            "job_id": job_id,
            "resume_id": resume_id,
            "match_result": match_result,
            "created_at": saved_match.get("created_at", now),
            "updated_at": saved_match.get("updated_at", now),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not process matching result: {str(exc)}",
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Job matching failed: {str(exc)}",
        ) from exc

# =========================================================
# JOBS - TAILOR RESUME
# =========================================================

@app.post("/jobs/{job_id}/tailor-resume")
def tailor_job_resume(
    job_id: str,
    resume_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(job_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid job ID"
        )

    if not ObjectId.is_valid(resume_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID"
        )

    job = jobs_collection.find_one({
        "_id": ObjectId(job_id),
        "user_id": user_id
    })

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    resume = resumes_collection.find_one({
        "_id": ObjectId(resume_id),
        "user_id": user_id
    })

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    # -----------------------------------------------------
    # SECURITY:
    # Only explicitly verified resume content can be used.
    # Never fall back to unverified extracted_text.
    # -----------------------------------------------------

    if resume.get("resume_verified") is not True:
        raise HTTPException(
            status_code=400,
            detail=(
                "Resume is not verified. "
                "Please extract and verify the resume text first."
            )
        )

    verified_resume = resume.get(
        "verified_resume_text"
    )

    if not verified_resume:
        raise HTTPException(
            status_code=400,
            detail=(
                "Verified resume text is not available. "
                "Please extract and verify the resume text first."
            )
        )

    job_data = dict(job)

    job_data["_id"] = str(
        job_data["_id"]
    )

    job_data["user_id"] = str(
        job_data.get(
            "user_id",
            user_id
        )
    )

    try:
        source_search_result_id = job_data.get(
            "source_search_result_id"
        )

        if ObjectId.is_valid(source_search_result_id):
            raw_search_result = (
                job_search_results_collection.find_one(
                    {
                        "_id": ObjectId(
                            source_search_result_id
                        ),
                        "user_id": user_id
                    },
                    {
                        "content": 1
                    }
                )
            )

            if raw_search_result:
                job_data["description"] = raw_search_result.get(
                    "content",
                    ""
                )[:MAX_JOB_CONTENT_LENGTH]

        result = tailor_resume(
            verified_resume=verified_resume,
            job=job_data
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Resume tailoring service failed: {str(error)}"
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Resume tailoring failed"
        )

    return {
        "message": "Resume tailoring completed",
        "job_id": job_id,
        "resume_id": resume_id,
        "result": result
    }


# =========================================================
# JOBS - GET ONE
# =========================================================

@app.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    if not ObjectId.is_valid(job_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid job ID"
        )

    job = jobs_collection.find_one({
        "_id": ObjectId(job_id),
        "user_id": get_user_id(current_user)
    })

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    job["_id"] = str(job["_id"])

    return job


# =========================================================
# JOBS - UPDATE
# =========================================================

@app.put("/jobs/{job_id}")
def update_job(
    job_id: str,
    job: Job,
    current_user: dict = Depends(get_current_user)
):
    if not ObjectId.is_valid(job_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid job ID"
        )

    result = jobs_collection.update_one(
        {
            "_id": ObjectId(job_id),
            "user_id": get_user_id(current_user)
        },
        {
            "$set": {
                **job.model_dump(),
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return {
        "message": "Job updated successfully"
    }


# =========================================================
# JOBS - DELETE
# =========================================================

@app.delete("/jobs/{job_id}")
def delete_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    if not ObjectId.is_valid(job_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid job ID"
        )

    result = jobs_collection.delete_one({
        "_id": ObjectId(job_id),
        "user_id": get_user_id(current_user)
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return {
        "message": "Job deleted successfully"
    }


# =========================================================
# AUTH - REGISTER
# =========================================================

@app.post("/users/register")
def register_user(user: User):
    email = user.email.strip().lower()
    name = user.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Name cannot be empty"
        )

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email cannot be empty"
        )

    if not user.password:
        raise HTTPException(
            status_code=400,
            detail="Password cannot be empty"
        )

    if not password_within_bcrypt_limit(user.password):
        raise HTTPException(
            status_code=400,
            detail=(
                "Password must be no more than "
                f"{MAX_BCRYPT_PASSWORD_BYTES} UTF-8 bytes."
            )
        )

    existing_user = users_collection.find_one({
        "email": email
    })

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail=(
                "Is email se account already exist karta hai. "
                "Please login karein."
            )
        )

    hashed_password = hash_password(user.password)

    user_data = {
        "name": name,
        "email": email,
        "password": hashed_password,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    try:
        result = users_collection.insert_one(
            user_data
        )

    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail=(
                "Is email se account already exist karta hai. "
                "Please login karein."
            )
        )

    return {
        "message": "User registered successfully",
        "user_id": str(result.inserted_id)
    }


@app.post("/users/forgot-password")
def forgot_password(request: ForgotPasswordRequest):
    email = request.email.strip().lower()

    try:
        mail_settings = get_password_reset_mail_settings()
    except PasswordResetDeliveryError as exc:
        logger.error("Password reset email configuration is invalid: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Password reset email is temporarily unavailable."
        ) from exc

    response = {
        "message": (
            "If an account exists for that email, a password reset link "
            "will be sent."
        )
    }
    user = users_collection.find_one({"email": email})

    if not user:
        return response

    now = datetime.now(timezone.utc)
    cooldown_start = now - timedelta(minutes=1)
    user_id = str(user["_id"])
    recent_request = password_reset_tokens_collection.find_one({
        "user_id": user_id,
        "created_at": {"$gte": cooldown_start}
    })

    if recent_request:
        return response

    token, token_hash = create_password_reset_token()
    expires_at = now + timedelta(minutes=30)
    inserted_token = password_reset_tokens_collection.insert_one({
        "user_id": user_id,
        "token_hash": token_hash,
        "created_at": now,
        "expires_at": expires_at
    })

    reset_url = build_password_reset_url(
        token,
        mail_settings.frontend_base_url
    )

    try:
        send_password_reset_email(
            email,
            reset_url,
            mail_settings
        )
    except PasswordResetDeliveryError as exc:
        password_reset_tokens_collection.delete_one({
            "_id": inserted_token.inserted_id
        })
        logger.exception("Could not deliver a password reset email.")
        raise HTTPException(
            status_code=503,
            detail="Could not send the password reset email. Please try again."
        ) from exc

    password_reset_tokens_collection.delete_many({
        "user_id": user_id,
        "_id": {"$ne": inserted_token.inserted_id}
    })

    return response


@app.post("/users/reset-password")
def reset_password(request: ResetPasswordRequest):
    if not request.token or len(request.token) > 256:
        raise HTTPException(
            status_code=400,
            detail="This password reset link is invalid or has expired."
        )

    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long."
        )

    if not password_within_bcrypt_limit(request.new_password):
        raise HTTPException(
            status_code=400,
            detail=(
                "Password must be no more than "
                f"{MAX_BCRYPT_PASSWORD_BYTES} UTF-8 bytes."
            )
        )

    password_hash = hash_password(request.new_password)
    now = datetime.now(timezone.utc)
    reset_token = password_reset_tokens_collection.find_one_and_delete({
        "token_hash": hash_password_reset_token(request.token),
        "expires_at": {"$gt": now}
    })

    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail="This password reset link is invalid or has expired."
        )

    user_id = reset_token["user_id"]
    try:
        object_user_id = ObjectId(user_id)
    except InvalidId as exc:
        logger.error("Password reset token contains an invalid user ID.")
        raise HTTPException(
            status_code=400,
            detail="This password reset link is invalid or has expired."
        ) from exc

    updated_user = users_collection.update_one(
        {"_id": object_user_id},
        {
            "$set": {
                "password": password_hash,
                "updated_at": now
            }
        }
    )

    if updated_user.matched_count == 0:
        raise HTTPException(
            status_code=400,
            detail="This password reset link is invalid or has expired."
        )

    active_sessions_collection.delete_many({"user_id": user_id})
    password_reset_tokens_collection.delete_many({"user_id": user_id})

    return {
        "message": "Password reset successfully. Please log in again."
    }


# =========================================================
# AUTH - LOGIN
# =========================================================

@app.post("/users/login")
def login_user(user: LoginUser):
    email = user.email.strip().lower()
    password = user.password

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email cannot be empty"
        )

    if not password:
        raise HTTPException(
            status_code=400,
            detail="Password cannot be empty"
        )

    existing_user = users_collection.find_one({
        "email": email
    })

    if not existing_user:
        raise HTTPException(
            status_code=401,
            detail=(
                "Email ya password galat hai. "
                "Please check karke dobara try karein."
            )
        )

    if not password_within_bcrypt_limit(password):
        raise HTTPException(
            status_code=401,
            detail=(
                "Email ya password galat hai. "
                "Please check karke dobara try karein."
            )
        )

    try:
        password_correct = verify_password(
            password,
            existing_user["password"]
        )

    except Exception as exc:
        logger.exception("Password verification failed for a stored user hash.")
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to verify credentials right now. "
                "Please try again later."
            )
        ) from exc

    if not password_correct:
        raise HTTPException(
            status_code=401,
            detail=(
                "Email ya password galat hai. "
                "Please check karke dobara try karein."
            )
        )

    user_id = str(existing_user["_id"])

    # -----------------------------------------------------
    # IMPORTANT:
    # Existing active session ko check karo.
    # Agar session expired hai to pehle delete karo.
    # Valid session hi second login ko block karega.
    # -----------------------------------------------------

    active_session = active_sessions_collection.find_one({
        "user_id": user_id
    })

    if active_session:

        session_expired = False

        session_expires_at = active_session.get(
            "expires_at"
        )

        if session_expires_at:

            if session_expires_at.tzinfo is None:
                session_expires_at = session_expires_at.replace(
                    tzinfo=timezone.utc
                )

            if session_expires_at <= datetime.now(
                timezone.utc
            ):
                session_expired = True

        else:
            # Session without expiry is treated as invalid
            # instead of blocking login indefinitely.
            session_expired = True

        if session_expired:

            active_sessions_collection.delete_one({
                "_id": active_session["_id"]
            })

        else:

            raise HTTPException(
                status_code=409,
                detail=(
                    "Ye account already login hai. "
                    "Pehle current session se logout karein, "
                    "uske baad login kar sakte hain."
                )
            )

    access_token = create_access_token(
        data={
            "sub": user_id
        },
        expires_delta=timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    try:
        token_payload = jwt.decode(
            access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        jti = token_payload.get("jti")
        exp = token_payload.get("exp")

        if not jti or not exp:
            raise HTTPException(
                status_code=500,
                detail="Failed to create login session"
            )

        expires_at = datetime.fromtimestamp(
            exp,
            tz=timezone.utc
        )

        active_sessions_collection.insert_one({
            "user_id": user_id,
            "jti": jti,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at
        })

    except HTTPException:
        raise

    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail=(
                "Ye account already login hai. "
                "Pehle current session se logout karein, "
                "uske baad login kar sakte hain."
            )
        )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id,
        "name": existing_user["name"],
        "email": existing_user["email"]
    }


# =========================================================
# AUTH - LOGOUT
# =========================================================

@app.post("/users/logout")
def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        jti = payload.get("jti")
        exp = payload.get("exp")

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )

    if not jti:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    expires_at = (
        datetime.fromtimestamp(
            exp,
            tz=timezone.utc
        )
        if exp
        else datetime.now(timezone.utc)
    )

    revoked_tokens_collection.update_one(
        {
            "jti": jti
        },
        {
            "$set": {
                "jti": jti,

                "user_id": get_user_id(
                    current_user
                ),

                "revoked_at": datetime.now(
                    timezone.utc
                ),

                "expires_at": expires_at
            }
        },
        upsert=True
    )

    active_sessions_collection.delete_one({
        "user_id": get_user_id(current_user),
        "jti": jti
    })

    return {
        "message": "Logout successful"
    }


# =========================================================
# AUTH - MY PROFILE
# =========================================================

@app.get("/users/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user)
):
    return {
        "user_id": get_user_id(current_user),

        "name": current_user["name"],

        "email": current_user["email"]
    }


@app.put("/users/me")
def update_my_profile(
    profile: ProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    name = profile.name.strip()
    email = profile.email.strip().lower()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Name cannot be empty."
        )

    if len(name) > 120:
        raise HTTPException(
            status_code=400,
            detail="Name must be no more than 120 characters."
        )

    if not email or "@" not in email:
        raise HTTPException(
            status_code=400,
            detail="Enter a valid email address."
        )

    if len(email) > 254:
        raise HTTPException(
            status_code=400,
            detail="Email must be no more than 254 characters."
        )

    user_id = get_user_id(current_user)
    try:
        update_result = users_collection.update_one(
            {"_id": current_user["_id"]},
            {
                "$set": {
                    "name": name,
                    "email": email,
                    "updated_at": datetime.now(timezone.utc),
                }
            }
        )
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists."
        ) from exc

    if update_result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="User account not found."
        )

    return {
        "message": "Profile updated successfully.",
        "user_id": user_id,
        "name": name,
        "email": email,
    }


# =========================================================
# RESUME - UPLOAD
# =========================================================

@app.post("/resumes")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    current_resume_count = resumes_collection.count_documents({
        "user_id": user_id
    })

    if current_resume_count >= MAX_RESUMES_PER_USER:
        raise HTTPException(
            status_code=400,
            detail="Maximum 3 resumes are allowed per user"
        )

    if file.content_type not in ALLOWED_RESUME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX resume files are allowed"
        )

    file_data = await file.read()

    if len(file_data) == 0:
        raise HTTPException(
            status_code=400,
            detail="Resume file cannot be empty"
        )

    if len(file_data) > MAX_RESUME_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Resume file size must be less than 5 MB"
        )

    now = datetime.now(timezone.utc)

    resume_data = {
        "user_id": user_id,

        "filename": file.filename,

        "content_type": file.content_type,

        "file_data": file_data,

        "file_size": len(file_data),

        "created_at": now,

        "updated_at": now
    }

    result = resumes_collection.insert_one(
        resume_data
    )

    return {
        "message": "Resume uploaded successfully",

        "resume_id": str(
            result.inserted_id
        ),

        "filename": file.filename,

        "file_size": len(file_data)
    }


# =========================================================
# RESUME - TEXT EXTRACTION TEST
# =========================================================

@app.post(
    "/resumes/text-extraction-test",
    dependencies=[Depends(get_current_user)],
)
async def resume_text_extraction_test(
    file: UploadFile = File(...),
):
    if file.content_type not in ALLOWED_RESUME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX resumes are allowed"
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Resume file is empty"
        )

    if len(file_bytes) > MAX_RESUME_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Resume file size must be less than 5 MB"
        )

    try:
        extracted_text = extract_resume_text(
            file_bytes=file_bytes,
            content_type=file.content_type
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    return {
        "message": "Resume text extraction successful",

        "filename": file.filename,

        "content_type": file.content_type,

        "text_length": len(extracted_text),

        "extracted_text": extracted_text
    }


# =========================================================
# RESUME - EXTRACT AND SAVE TEXT
# =========================================================

@app.post("/resumes/{resume_id}/extract-text")
async def extract_and_save_resume_text(
    resume_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(resume_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID"
        )

    resume = resumes_collection.find_one({
        "_id": ObjectId(resume_id),
        "user_id": user_id
    })

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    file_data = resume.get("file_data")

    if not file_data:
        raise HTTPException(
            status_code=400,
            detail="Resume file data is missing"
        )

    content_type = resume.get("content_type")

    if content_type not in ALLOWED_RESUME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported resume file type"
        )

    try:
        extracted_text = extract_resume_text(
            file_bytes=file_data,
            content_type=content_type
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    try:
        verified_resume = verify_resume_text(
            resume_text=extracted_text
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    now = datetime.now(timezone.utc)

    resumes_collection.update_one(
        {
            "_id": ObjectId(resume_id),
            "user_id": user_id
        },
        {
            "$set": {
                "extracted_text": extracted_text,

                "text_length": len(
                    extracted_text
                ),

                "text_extracted_at": now,

                "resume_verified": verified_resume[
                    "verified"
                ],

                "resume_source": verified_resume[
                    "source"
                ],

                "verified_resume_text": verified_resume[
                    "resume_text"
                ],

                "resume_verified_at": now,

                "updated_at": now
            }
        }
    )

    return {
        "message": (
            "Resume text extracted, verified and "
            "saved successfully"
        ),

        "resume_id": resume_id,

        "text_length": len(
            extracted_text
        ),

        "resume_verified": verified_resume[
            "verified"
        ],

        "resume_source": verified_resume[
            "source"
        ],

        "extracted_text": extracted_text
    }


# =========================================================
# RESUME - LIST MY RESUMES
# =========================================================

@app.get("/resumes")
def get_my_resumes(
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    resumes = list(
        resumes_collection.find(
            {
                "user_id": user_id
            },
            {
                "file_data": 0
            }
        ).sort(
            "created_at",
            -1
        )
    )

    for resume in resumes:
        resume["_id"] = str(resume["_id"])

    return resumes


# =========================================================
# RESUME - GET ONE
# =========================================================

@app.get("/resumes/{resume_id}")
def get_resume(
    resume_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(resume_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID"
        )

    resume = resumes_collection.find_one(
        {
            "_id": ObjectId(resume_id),
            "user_id": user_id
        },
        {
            "file_data": 0
        }
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    resume["_id"] = str(
        resume["_id"]
    )

    return resume


# =========================================================
# RESUME - UPDATE / REPLACE FILE
# =========================================================

@app.put("/resumes/{resume_id}")
async def update_resume(
    resume_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(resume_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID"
        )

    if file.content_type not in ALLOWED_RESUME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX resume files are allowed"
        )

    file_data = await file.read()

    if len(file_data) == 0:
        raise HTTPException(
            status_code=400,
            detail="Resume file cannot be empty"
        )

    if len(file_data) > MAX_RESUME_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Resume file size must be less than 5 MB"
        )

    now = datetime.now(timezone.utc)

    result = resumes_collection.update_one(
        {
            "_id": ObjectId(resume_id),
            "user_id": user_id
        },
        {
            "$set": {
                "filename": file.filename,

                "content_type": file.content_type,

                "file_data": file_data,

                "file_size": len(file_data),

                "updated_at": now
            },

            "$unset": {
                "extracted_text": "",
                "text_length": "",
                "text_extracted_at": "",
                "resume_verified": "",
                "resume_source": "",
                "verified_resume_text": "",
                "resume_verified_at": ""
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    return {
        "message": "Resume updated successfully",

        "resume_id": resume_id,

        "filename": file.filename,

        "file_size": len(file_data)
    }


# =========================================================
# RESUME - DELETE
# =========================================================

@app.delete("/resumes/{resume_id}")
def delete_resume(
    resume_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(resume_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID"
        )

    result = resumes_collection.delete_one({
        "_id": ObjectId(resume_id),
        "user_id": user_id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    return {
        "message": "Resume deleted successfully"
    }


# =========================================================
# USER PREFERENCES - CREATE
# =========================================================

@app.post("/preferences")
def create_preferences(
    preferences: UserPreferences,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    existing_preferences = preferences_collection.find_one({
        "user_id": user_id
    })

    if existing_preferences:
        raise HTTPException(
            status_code=400,
            detail=(
                "Preferences already exist. "
                "Use PUT /preferences to update them."
            )
        )

    now = datetime.now(timezone.utc)

    preferences_data = preferences.model_dump()

    preferences_data["user_id"] = user_id
    preferences_data["created_at"] = now
    preferences_data["updated_at"] = now

    try:
        result = preferences_collection.insert_one(
            preferences_data
        )

    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="Preferences already exist"
        )

    return {
        "message": "Preferences created successfully",

        "preference_id": str(
            result.inserted_id
        )
    }


# =========================================================
# USER PREFERENCES - GET
# =========================================================

@app.get("/preferences")
def get_preferences(
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    preferences = preferences_collection.find_one(
        {
            "user_id": user_id
        },
        {
            "_id": 0
        }
    )

    if not preferences:
        raise HTTPException(
            status_code=404,
            detail="Preferences not found"
        )

    return preferences


# =========================================================
# USER PREFERENCES - UPDATE
# =========================================================

@app.put("/preferences")
def update_preferences(
    preferences: UserPreferences,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    existing_preferences = preferences_collection.find_one({
        "user_id": user_id
    })

    if not existing_preferences:
        raise HTTPException(
            status_code=404,
            detail=(
                "Preferences not found. "
                "Use POST /preferences first."
            )
        )

    updated_data = preferences.model_dump()

    updated_data["updated_at"] = datetime.now(
        timezone.utc
    )

    preferences_collection.update_one(
        {
            "user_id": user_id
        },
        {
            "$set": updated_data
        }
    )

    return {
        "message": "Preferences updated successfully"
    }


# =========================================================
# TAVILY JOB SEARCH API
# =========================================================


@app.get("/jobs/search/tavily")
def search_jobs_with_tavily(
    query: str | None = None,
    job_title: str | None = None,
    location: str | None = None,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    preferences = preferences_collection.find_one({
        "user_id": user_id
    })

    if not preferences and not query:
        raise HTTPException(
            status_code=404,
            detail="Please create your job preferences first"
        )

    try:
        result = search_and_store_jobs(
            tavily_client=tavily_client,
            job_search_results_collection=(
                job_search_results_collection
            ),
            user_id=user_id,
            preferences=preferences,
            query=query,
            job_title_query=job_title,
            location_query=location,
            max_job_content_length=MAX_JOB_CONTENT_LENGTH,
            max_results_per_user=MAX_JOB_SEARCH_RESULTS_PER_USER
        )

        result["message"] = (
            "Search results are ready. Save individual job postings "
            "to add them to Saved Jobs."
        )

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Tavily job search failed"
        )
# =========================================================
# LANGCHAIN JOB AGENT API
# =========================================================

@app.post("/jobs/agent")
def run_job_agent(
    request: JobAgentRequest,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    try:
        from app.agents.job_agent import job_agent

        result = job_agent.invoke({
            "messages": [
                {
                    "role": "user",
                    "content": request.message.strip()
                }
            ]
        }, context={
            "user_id": user_id
        })

        messages = result.get(
            "messages",
            []
        )

        if not messages:
            raise RuntimeError(
                "Job agent returned no messages"
            )

        last_message = messages[-1]

        response_content = last_message.content

        if isinstance(
            response_content,
            list
        ):
            response_content = " ".join(
                item.get("text", "")
                for item in response_content
                if isinstance(item, dict)
            )

        return {
            "message": "Job agent completed",
            "response": response_content
        }

    except Exception as error:

        error_message = str(error)

        if (
            "429" in error_message
            or "RESOURCE_EXHAUSTED" in error_message
            or "quota" in error_message.lower()
        ):
            raise HTTPException(
                status_code=429,
                detail=(
                    "Gemini API quota is currently exhausted. "
                    "Please try again later."
                )
            )

        raise HTTPException(
            status_code=500,
            detail="Job agent failed"
        )


# =========================================================
# APPLICATIONS - CREATE / SAVE
# =========================================================

@app.post("/applications")
def create_application(
    application: Application,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(application.job_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid job ID"
        )

    if not ObjectId.is_valid(application.resume_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID"
        )

    current_application_count = (
        applications_collection.count_documents({
            "user_id": user_id
        })
    )

    if current_application_count >= MAX_APPLICATIONS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail="Maximum saved applications limit reached"
        )

    job = jobs_collection.find_one({
        "_id": ObjectId(application.job_id),
        "user_id": user_id
    })

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    resume = resumes_collection.find_one({
        "_id": ObjectId(application.resume_id),
        "user_id": user_id
    })

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    existing_application = applications_collection.find_one({
        "user_id": user_id,
        "job_id": application.job_id,
        "resume_id": application.resume_id
    })

    if existing_application:
        return {
            "message": "Application already exists",

            "application_id": str(
                existing_application["_id"]
            ),

            "status": existing_application.get(
                "status",
                "saved"
            )
        }

    application_data = application.model_dump()

    application_data["user_id"] = user_id

    application_data["application_url"] = job.get(
        "application_url",
        application.application_url
    )

    now = datetime.now(timezone.utc)

    application_data["created_at"] = now
    application_data["updated_at"] = now

    try:
        result = applications_collection.insert_one(
            application_data
        )

    except DuplicateKeyError:

        # Database-level protection handles race conditions.
        existing_application = applications_collection.find_one({
            "user_id": user_id,
            "job_id": application.job_id,
            "resume_id": application.resume_id
        })

        if existing_application:
            return {
                "message": "Application already exists",

                "application_id": str(
                    existing_application["_id"]
                ),

                "status": existing_application.get(
                    "status",
                    "saved"
                )
            }

        raise HTTPException(
            status_code=409,
            detail="Application already exists"
        )

    return {
        "message": "Application saved successfully",

        "application_id": str(
            result.inserted_id
        ),

        "job_id": application.job_id,

        "resume_id": application.resume_id,

        "status": application_data["status"],

        "application_url": application_data[
            "application_url"
        ]
    }


# =========================================================
# APPLICATIONS - GET MY APPLICATIONS
# =========================================================

@app.get("/applications")
def get_applications(
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    applications = applications_collection.find({
        "user_id": user_id
    }).sort(
        "created_at",
        -1
    )

    results = []

    for application in applications:

        job = None

        job_id = application.get(
            "job_id"
        )

        if job_id and ObjectId.is_valid(job_id):
            job = jobs_collection.find_one({
                "_id": ObjectId(job_id),
                "user_id": user_id
            })

        application_url = (
            application.get("application_url")
            or (job or {}).get("application_url", "")
        )
        job_title = (job or {}).get("title", "")

        if (
            _is_listing_page(job_title, application_url)
            or _is_non_job_resource(job_title, application_url)
        ):
            continue

        results.append({
            "application_id": str(
                application["_id"]
            ),

            "job_id": job_id,

            "resume_id": application.get(
                "resume_id"
            ),

            "job": {
                "title": (
                    job.get(
                        "title",
                        "Not specified"
                    )
                    if job
                    else "Not specified"
                ),

                "company": (
                    job.get(
                        "company",
                        "Not specified"
                    )
                    if job
                    else "Not specified"
                ),

                "location": (
                    job.get(
                        "location",
                        "Not specified"
                    )
                    if job
                    else "Not specified"
                )
            },

            "status": application.get(
                "status",
                "saved"
            ),

            "approved": application.get(
                "approved",
                False
            ),

            "requires_user_review": application.get(
                "requires_user_review",
                True
            ),

            "application_url": application.get(
                "application_url",
                "Not specified"
            ),

            "applied_at": application.get(
                "applied_at"
            ),

            "notes": application.get(
                "notes",
                ""
            ),

            "created_at": application.get(
                "created_at"
            ),

            "updated_at": application.get(
                "updated_at"
            )
        })

    return {
        "message": "Applications fetched successfully",

        "total_applications": len(results),

        "applications": results
    }


# =========================================================
# APPLICATIONS - DELETE
# =========================================================

@app.delete("/applications/{application_id}")
def delete_application(
    application_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(application_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid application ID"
        )

    result = applications_collection.delete_one({
        "_id": ObjectId(application_id),
        "user_id": user_id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    return {
        "message": "Application deleted successfully",
        "application_id": application_id
    }


# =========================================================
# APPLICATIONS - PREPARE
# =========================================================

@app.post("/applications/prepare")
def prepare_application(
    preparation: ApplicationPreparation,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(preparation.job_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid job ID"
        )

    if not ObjectId.is_valid(preparation.resume_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID"
        )

    job = jobs_collection.find_one({
        "_id": ObjectId(preparation.job_id),
        "user_id": user_id
    })

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    job_url = job.get("application_url", "")
    if (
        _is_listing_page(job.get("title", ""), job_url)
        or _is_non_job_resource(job.get("title", ""), job_url)
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "This saved item is a company or job-search page, not an "
                "individual job posting, so it cannot be added to the "
                "application tracker."
            )
        )

    resume = resumes_collection.find_one({
        "_id": ObjectId(preparation.resume_id),
        "user_id": user_id
    })

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    # -----------------------------------------------------
    # SECURITY:
    # Application preparation also requires explicit
    # resume verification.
    # -----------------------------------------------------

    if resume.get("resume_verified") is not True:
        raise HTTPException(
            status_code=400,
            detail=(
                "Resume is not verified. "
                "Please extract and verify the resume text first."
            )
        )

    resume_text = resume.get(
        "verified_resume_text"
    )

    if not resume_text:
        raise HTTPException(
            status_code=400,
            detail=(
                "Verified resume text is not available. "
                "Please extract and verify the resume text first."
            )
        )

    # -----------------------------------------------------
    # IMPORTANT:
    # Any existing application with the same
    # user + job + resume combination counts as duplicate.
    # Do not filter only by requires_user_review.
    # -----------------------------------------------------

    existing_application = applications_collection.find_one({
        "user_id": user_id,
        "job_id": preparation.job_id,
        "resume_id": preparation.resume_id
    })

    if existing_application:
        return {
            "message": "Application preparation already exists",

            "application_id": str(
                existing_application["_id"]
            ),

            "job_id": preparation.job_id,

            "resume_id": preparation.resume_id,

            "requires_user_review": existing_application.get(
                "requires_user_review",
                True
            ),

            "approved": existing_application.get(
                "approved",
                False
            ),

            "status": existing_application.get(
                "status",
                "saved"
            ),

            "application_url": existing_application.get(
                "application_url",
                job.get(
                    "application_url",
                    "Not specified"
                )
            )
        }

    now = datetime.now(timezone.utc)

    preparation_data = {
        "user_id": user_id,

        "job_id": preparation.job_id,

        "resume_id": preparation.resume_id,

        "cover_letter": preparation.cover_letter,

        "application_answers": preparation.application_answers,

        "notes": preparation.notes,

        "requires_user_review": True,

        "approved": False,

        "status": "discovered",

        "application_url": job.get(
            "application_url",
            "Not specified"
        ),

        "created_at": now,

        "updated_at": now
    }

    try:
        result = applications_collection.insert_one(
            preparation_data
        )

    except DuplicateKeyError:

        # Race-condition protection.
        existing_application = applications_collection.find_one({
            "user_id": user_id,
            "job_id": preparation.job_id,
            "resume_id": preparation.resume_id
        })

        if existing_application:
            return {
                "message": "Application preparation already exists",

                "application_id": str(
                    existing_application["_id"]
                ),

                "job_id": preparation.job_id,

                "resume_id": preparation.resume_id,

                "requires_user_review": existing_application.get(
                    "requires_user_review",
                    True
                ),

                "approved": existing_application.get(
                    "approved",
                    False
                ),

                "status": existing_application.get(
                    "status",
                    "saved"
                ),

                "application_url": existing_application.get(
                    "application_url",
                    job.get(
                        "application_url",
                        "Not specified"
                    )
                )
            }

        raise HTTPException(
            status_code=409,
            detail="Application already exists"
        )

    return {
        "message": "Application prepared successfully",

        "application_id": str(
            result.inserted_id
        ),

        "job_id": preparation.job_id,

        "resume_id": preparation.resume_id,

        "requires_user_review": True,

        "approved": False,

        "status": "discovered",

        "application_url": job.get(
            "application_url",
            "Not specified"
        )
    }


# =========================================================
# APPLICATIONS - APPROVE
# =========================================================

@app.post("/applications/{application_id}/approve")
def approve_application(
    application_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(application_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid application ID"
        )

    application = applications_collection.find_one({
        "_id": ObjectId(application_id),
        "user_id": user_id
    })

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    ensure_application_is_individual_job(application)

    if not application.get(
        "requires_user_review",
        True
    ):
        raise HTTPException(
            status_code=400,
            detail="Application does not require review"
        )

    updated_at = datetime.now(timezone.utc)

    applications_collection.update_one(
        {
            "_id": ObjectId(application_id),
            "user_id": user_id
        },
        {
            "$set": {
                "approved": True,

                "requires_user_review": False,

                "status": "ready-to-apply",

                "updated_at": updated_at
            }
        }
    )

    return {
        "message": "Application approved successfully",

        "application_id": application_id,

        "approved": True,

        "requires_user_review": False,

        "status": "ready-to-apply",

        "updated_at": updated_at
    }


# =========================================================
# APPLICATIONS - SUBMISSION SAFETY GATE
# =========================================================

@app.post("/applications/{application_id}/submit-gate")
def application_submission_gate(
    application_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(application_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid application ID"
        )

    application = applications_collection.find_one({
        "_id": ObjectId(application_id),
        "user_id": user_id
    })

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    ensure_application_is_individual_job(application)

    try:
        gate_result = check_submission_gate(
            application
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    if not gate_result.get(
        "allowed",
        False
    ):
        return {
            "message": "Application cannot proceed",

            "application_id": application_id,

            "gate": gate_result,

            "submitted": False
        }

    application_url = application.get(
        "application_url"
    )

    if not application_url:
        raise HTTPException(
            status_code=400,
            detail="Application URL is not available"
        )

    try:
        verification_result = verify_application_url(
            application_url
        )

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Application URL verification failed: {str(error)}"
        )

    if not verification_result.get(
        "valid",
        False
    ):
        return {
            "message": "Application URL could not be verified",

            "application_id": application_id,

            "gate": gate_result,

            "url_verified": False,

            "verification": verification_result,

            "submitted": False
        }

    return {
        "message": (
            "Application passed the final safety gate. "
            "Human confirmation is required before submission."
        ),

        "application_id": application_id,

        "gate": gate_result,

        "url_verified": True,

        "verification": verification_result,

        "submitted": False,

        "requires_final_human_confirmation": True,

        "safety_note": (
            "No application was submitted. "
            "Final human confirmation is required."
        )
    }


# =========================================================
# APPLICATIONS - UPDATE STATUS
# =========================================================

@app.patch("/applications/{application_id}/status")
def update_application_status(
    application_id: str,
    status: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(application_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid application ID"
        )

    allowed_statuses = {
        "saved",
        "discovered",
        "shortlisted",
        "ready-to-apply",
        "applied",
        "interview",
        "rejected"
    }

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid status. Allowed statuses: "
                + ", ".join(
                    sorted(allowed_statuses)
                )
            )
        )

    application = applications_collection.find_one({
        "_id": ObjectId(application_id),
        "user_id": user_id
    })

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    updated_at = datetime.now(timezone.utc)

    update_data = {
        "status": status,
        "updated_at": updated_at
    }

    if status == "applied":
        update_data["applied_at"] = updated_at

    applications_collection.update_one(
        {
            "_id": ObjectId(application_id),
            "user_id": user_id
        },
        {
            "$set": update_data
        }
    )

    return {
        "message": "Application status updated successfully",

        "application_id": application_id,

        "status": status,

        "updated_at": updated_at
    }


# =========================================================
# APPLICATIONS - OPEN APPLICATION PAGE
# =========================================================

@app.post("/applications/{application_id}/open")
def open_application(
    application_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(application_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid application ID"
        )

    application = applications_collection.find_one({
        "_id": ObjectId(application_id),
        "user_id": user_id
    })

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    ensure_application_is_individual_job(application)

    if not application.get(
        "approved",
        False
    ):
        raise HTTPException(
            status_code=400,
            detail="Application has not been approved"
        )

    if application.get(
        "requires_user_review",
        True
    ):
        raise HTTPException(
            status_code=400,
            detail="Application still requires user review"
        )

    if application.get(
        "status"
    ) != "ready-to-apply":
        raise HTTPException(
            status_code=400,
            detail="Application is not ready to apply"
        )

    application_url = application.get(
        "application_url"
    )

    if not application_url or application_url == "Not specified":
        raise HTTPException(
            status_code=400,
            detail="Application URL is not available"
        )

    try:
        verification_result = verify_application_url(
            application_url
        )

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Application URL verification failed: {str(error)}"
        )

    if not verification_result.get(
        "valid",
        False
    ):
        return {
            "message": "Application URL could not be verified",

            "application_id": application_id,

            "status": "ready-to-apply",

            "application_url": application_url,

            "verification": verification_result
        }

    try:
        browser_result = open_application_page_for_user(
            application_url
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to open application page"
        )

    if browser_result.get(
        "redirected",
        False
    ):
        return {
            "message": (
                "Application page unavailable "
                "because the URL redirected"
            ),

            "application_id": application_id,

            "status": "ready-to-apply",

            "application_url": application_url,

            "browser": browser_result
        }

    return {
        "message": "Application page opened successfully",

        "application_id": application_id,

        "status": "ready-to-apply",

        "application_url": application_url,

        "browser": browser_result
    }


# =========================================================
# APPLICATIONS - INSPECT APPLICATION PAGE
# =========================================================

@app.post("/applications/{application_id}/inspect")
def inspect_application(
    application_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(application_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid application ID"
        )

    application = applications_collection.find_one({
        "_id": ObjectId(application_id),
        "user_id": user_id
    })

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    ensure_application_is_individual_job(application)

    application_url = application.get(
        "application_url"
    )

    if not application_url:
        raise HTTPException(
            status_code=400,
            detail="Application URL is not available"
        )

    try:
        verification_result = verify_application_url(
            application_url
        )

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Application URL verification failed: {str(error)}"
        )

    if not verification_result.get(
        "valid",
        False
    ):
        return {
            "message": "Application URL could not be verified",

            "application_id": application_id,

            "application_url": application_url,

            "url_verified": False,

            "verification": verification_result
        }

    try:
        inspection_result = inspect_application_page(
            application_url
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Application page inspection failed"
        )

    return {
        "message": "Application page inspected successfully",

        "application_id": application_id,

        "application_url": application_url,

        "url_verified": True,

        "verification": verification_result,

        "inspection": inspection_result,

        "safety_note": (
            "Application page was inspected without "
            "submitting the form."
        )
    }


# =========================================================
# APPLICATIONS - MAP VERIFIED RESUME TO FORM FIELDS
# =========================================================

@app.post("/applications/{application_id}/map-fields")
def map_application_fields_for_application(
    application_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    if not ObjectId.is_valid(application_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid application ID"
        )

    application = applications_collection.find_one({
        "_id": ObjectId(application_id),
        "user_id": user_id
    })

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    job_id = application.get(
        "job_id"
    )

    resume_id = application.get(
        "resume_id"
    )

    if not job_id:
        raise HTTPException(
            status_code=400,
            detail="Application job ID is missing"
        )

    if not resume_id:
        raise HTTPException(
            status_code=400,
            detail="Application resume ID is missing"
        )

    if not ObjectId.is_valid(job_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid job ID"
        )

    if not ObjectId.is_valid(resume_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID"
        )

    job = jobs_collection.find_one({
        "_id": ObjectId(job_id),
        "user_id": user_id
    })

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    ensure_application_is_individual_job({
        **application,
        "application_url": job.get(
            "application_url",
            application.get("application_url", ""),
        ),
    })

    resume = resumes_collection.find_one({
        "_id": ObjectId(resume_id),
        "user_id": user_id
    })

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    # -----------------------------------------------------
    # SECURITY:
    # Only explicitly verified resume content is allowed.
    # Never fall back to extracted_text.
    # -----------------------------------------------------

    if resume.get("resume_verified") is not True:
        raise HTTPException(
            status_code=400,
            detail=(
                "Resume is not verified. "
                "Please extract and verify the resume text first."
            )
        )

    verified_resume = resume.get(
        "verified_resume_text"
    )

    if not verified_resume:
        raise HTTPException(
            status_code=400,
            detail=(
                "Verified resume text is not available. "
                "Please extract and verify the resume text first."
            )
        )

    application_url = application.get(
        "application_url"
    )

    if not application_url:
        raise HTTPException(
            status_code=400,
            detail="Application URL is not available"
        )

    try:
        verification_result = verify_application_url(
            application_url
        )

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Application URL verification failed: {str(error)}"
        )

    if not verification_result.get(
        "valid",
        False
    ):
        return {
            "message": "Application URL could not be verified",

            "application_id": application_id,

            "url_verified": False,

            "verification": verification_result
        }

    try:
        inspection_result = inspect_application_page(
            application_url
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Application page inspection failed"
        )

    fields = []

    for form in inspection_result.get(
        "forms",
        []
    ):
        for field in form.get(
            "inputs",
            []
        ):
            if field.get("name"):
                fields.append({
                    "name": field.get(
                        "name"
                    ),

                    "id": field.get(
                        "id"
                    ),

                    "tag": field.get(
                        "tag"
                    ),

                    "type": field.get(
                        "type"
                    ),

                    "placeholder": field.get(
                        "placeholder"
                    )
                })

    try:
        mapping_result = map_application_fields(
            verified_resume=verified_resume,
            fields=fields
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Application field mapping failed"
        )

    return {
        "message": "Application fields mapped safely",

        "application_id": application_id,

        "resume_id": resume_id,

        "form_count": inspection_result.get(
            "form_count",
            0
        ),

        "fields_found": len(fields),

        "mapping": mapping_result,

        "safety_note": (
            "Only information available in the verified "
            "resume was mapped. Missing information was "
            "not invented. No form was submitted."
        )
    }

# =========================================================
# DASHBOARD SUMMARY
# =========================================================

@app.get("/dashboard/summary")
def get_dashboard_summary(
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)

    search_results = job_search_results_collection.find(
        {"user_id": user_id},
        {
            "title": 1,
            "url": 1,
            "content": 1,
            "location": 1,
            "job_title_query": 1,
            "location_query": 1,
        },
    )
    jobs_found = sum(
        _is_visible_search_result(result)
        for result in search_results
    )

    stored_jobs = list(jobs_collection.find(
        {"user_id": user_id},
        {"title": 1, "application_url": 1},
    ))
    jobs_by_id = {
        str(job["_id"]): job
        for job in stored_jobs
    }
    saved_jobs = sum(
        not (
            _is_listing_page(
                job.get("title", ""),
                job.get("application_url", ""),
            )
            or _is_non_job_resource(
                job.get("title", ""),
                job.get("application_url", ""),
            )
        )
        for job in stored_jobs
    )

    # Number of stored resume-job matches.
    matched_jobs = job_matches_collection.count_documents({
        "user_id": user_id
    })

    tracked_applications = applications_collection.find(
        {"user_id": user_id},
        {"job_id": 1, "application_url": 1},
    )
    applications = 0
    for application in tracked_applications:
        job = jobs_by_id.get(application.get("job_id"))
        application_url = (
            application.get("application_url")
            or (job or {}).get("application_url", "")
        )
        job_title = (job or {}).get("title", "")
        if (
            _is_listing_page(job_title, application_url)
            or _is_non_job_resource(job_title, application_url)
        ):
            continue
        applications += 1

    return {
        "jobs_found": jobs_found,
        "saved_jobs": saved_jobs,
        "matched_jobs": matched_jobs,
        "applications": applications
    }