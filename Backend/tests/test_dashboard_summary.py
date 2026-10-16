from bson import ObjectId

from app import main


class FakeCollection:
    def __init__(self, documents=()):
        self.documents = list(documents)

    def find(self, query, projection=None):
        documents = [
            document
            for document in self.documents
            if document.get("user_id") == query["user_id"]
        ]
        if projection is None:
            return documents
        return [
            {
                key: value
                for key, value in document.items()
                if key == "_id" or projection.get(key)
            }
            for document in documents
        ]

    def count_documents(self, query):
        return sum(
            all(document.get(key) == value for key, value in query.items())
            for document in self.documents
        )


def test_dashboard_counts_only_visible_job_and_application_records(
    monkeypatch,
):
    user_id = "dashboard-test-user"
    visible_job_id = ObjectId()
    hidden_job_id = ObjectId()

    monkeypatch.setattr(
        main,
        "job_search_results_collection",
        FakeCollection([
            {
                "user_id": user_id,
                "title": "Software Engineer",
                "url": "https://jobs.example.test/postings/123",
            },
            {
                "user_id": user_id,
                "title": "Software Engineer jobs",
                "url": "https://www.linkedin.com/jobs/search/?keywords=engineer",
            },
            {
                "user_id": user_id,
                "title": "Software Engineer",
                "url": "https://unlisted-jobs.example.test/software-engineer",
                "url_verified": False,
                "verification_status": "manual_review_required",
            },
            {
                "user_id": user_id,
                "title": "BDE Field Sales",
                "url": "https://jobs.example.test/bde",
                "job_title_query": "custom",
                "location_query": "custom",
            },
            {
                "user_id": user_id,
                "title": "React Developer",
                "url": "https://jobs.example.test/react",
                "job_title_query": "React Developer",
                "location_query": "Hyderabad",
                "location": "Chennai",
                "content": "Location: Chennai",
            },
        ]),
    )
    monkeypatch.setattr(
        main,
        "jobs_collection",
        FakeCollection([
            {
                "_id": visible_job_id,
                "user_id": user_id,
                "title": "Software Engineer",
                "application_url": "https://jobs.example.test/postings/123",
            },
            {
                "_id": hidden_job_id,
                "user_id": user_id,
                "title": "Company reviews",
                "application_url": "https://example.test/reviews/company",
            },
        ]),
    )
    monkeypatch.setattr(
        main,
        "job_matches_collection",
        FakeCollection([
            {"user_id": user_id},
            {"user_id": user_id},
            {"user_id": user_id},
            {"user_id": "other-user"},
        ]),
    )
    monkeypatch.setattr(
        main,
        "applications_collection",
        FakeCollection([
            {
                "user_id": user_id,
                "job_id": str(visible_job_id),
                "application_url": "https://jobs.example.test/postings/123",
            },
            {
                "user_id": user_id,
                "job_id": str(hidden_job_id),
                "application_url": "https://example.test/reviews/company",
            },
        ]),
    )

    result = main.get_dashboard_summary({"_id": user_id})

    assert result == {
        "jobs_found": 2,
        "saved_jobs": 1,
        "matched_jobs": 3,
        "applications": 1,
    }
