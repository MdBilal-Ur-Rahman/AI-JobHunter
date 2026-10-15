import os
from uuid import uuid4

import pytest
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError


MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017",
)

DB_NAME = "ai-jobhunter"


@pytest.fixture
def applications_collection():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)

    try:
        client.admin.command("ping")
    except Exception as exc:
        client.close()
        pytest.skip(f"MongoDB is not reachable: {exc}")

    collection_name = f"test_applications_{uuid4().hex}"
    collection = client[DB_NAME][collection_name]
    collection.create_index(
        [
            ("user_id", 1),
            ("job_id", 1),
            ("resume_id", 1),
        ],
        unique=True,
    )

    user_id = f"test-user-{uuid4()}"
    job_id = f"test-job-{uuid4()}"
    resume_id = f"test-resume-{uuid4()}"

    yield collection, user_id, job_id, resume_id

    collection.drop()
    client.close()


def test_same_user_job_resume_cannot_be_duplicated(
    applications_collection,
):
    collection, user_id, job_id, resume_id = applications_collection

    first_application = {
        "user_id": user_id,
        "job_id": job_id,
        "resume_id": resume_id,
        "status": "saved",
    }

    second_application = {
        "user_id": user_id,
        "job_id": job_id,
        "resume_id": resume_id,
        "status": "saved",
    }

    collection.insert_one(first_application)

    with pytest.raises(DuplicateKeyError):
        collection.insert_one(second_application)

    count = collection.count_documents({
        "user_id": user_id,
        "job_id": job_id,
        "resume_id": resume_id,
    })

    assert count == 1


def test_same_job_different_resume_is_allowed(
    applications_collection,
):
    collection, user_id, job_id, resume_id = applications_collection

    first_application = {
        "user_id": user_id,
        "job_id": job_id,
        "resume_id": resume_id,
        "status": "saved",
    }

    second_application = {
        "user_id": user_id,
        "job_id": job_id,
        "resume_id": f"another-resume-{uuid4()}",
        "status": "saved",
    }

    collection.insert_one(first_application)
    collection.insert_one(second_application)

    count = collection.count_documents({
        "user_id": user_id,
        "job_id": job_id,
    })

    assert count == 2