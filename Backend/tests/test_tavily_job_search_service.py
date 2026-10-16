import pytest

from app.services import tavily_job_search_service
from app import main


class FakeCursor(list):
    def limit(self, count):
        return FakeCursor(self[:count])

    def sort(self, key, direction):
        return FakeCursor(
            sorted(
                self,
                key=lambda document: document.get(key),
                reverse=direction < 0,
            )
        )


class FakeCollection:
    def __init__(self, documents=()):
        self.documents = list(documents)

    def find_one(self, query, sort=None):
        matching = [
            document
            for document in self.documents
            if all(document.get(key) == value for key, value in query.items())
        ]
        if sort:
            key, direction = sort[0]
            matching.sort(key=lambda document: document.get(key), reverse=direction < 0)
        return matching[0] if matching else None

    def find(self, query, projection=None):
        matching = [
            document
            for document in self.documents
            if all(document.get(key) == value for key, value in query.items())
        ]
        if projection is not None:
            matching = [
                {
                    key: value
                    for key, value in document.items()
                    if key == "_id" or projection.get(key)
                }
                for document in matching
            ]
        return FakeCursor(matching)

    def count_documents(self, query):
        return len(self.find(query))

    def insert_one(self, document):
        from bson import ObjectId

        stored = dict(document)
        stored["_id"] = ObjectId()
        self.documents.append(stored)

        class InsertResult:
            inserted_id = stored["_id"]

        return InsertResult()

    def update_one(self, query, update):
        for document in self.documents:
            if all(document.get(key) == value for key, value in query.items()):
                document.update(update.get("$set", {}))
                return
        raise AssertionError("Expected document to update")

    def delete_one(self, query):
        for index, document in enumerate(self.documents):
            if all(document.get(key) == value for key, value in query.items()):
                self.documents.pop(index)

                class DeleteResult:
                    deleted_count = 1

                return DeleteResult()

        class DeleteResult:
            deleted_count = 0

        return DeleteResult()


class FakeTavilyClient:
    def __init__(self, results):
        self.results = results
        self.queries = []

    def search(self, **kwargs):
        self.queries.append(kwargs)
        return {"results": self.results}


def test_search_skips_informational_results_before_url_verification(
    monkeypatch,
):
    client = FakeTavilyClient([
        {
            "title": "React (software) - Wikipedia",
            "url": "https://en.wikipedia.org/wiki/React_(software)",
        },
        {
            "title": "React Developer - Example Corp",
            "url": "https://jobs.example.test/react-developer",
        },
    ])
    collection = object()

    def fail_if_verified(url):
        raise AssertionError(f"Informational URL was verified: {url}")

    monkeypatch.setattr(
        tavily_job_search_service,
        "verify_application_url",
        fail_if_verified,
    )

    result = tavily_job_search_service.search_and_store_jobs(
        tavily_client=client,
        job_search_results_collection=collection,
        user_id="test-user",
        query="React jobs in Toronto",
    )

    assert result["total_non_job_results"] == 1
    assert result["searches"][0]["non_job_result_count"] == 1
    assert "exclude tutorials" in client.queries[0]["query"]
    assert "job openings" in client.queries[0]["query"]
    assert "apply" in client.queries[0]["query"]
    assert client.queries[0]["max_results"] == 20
    assert "linkedin.com" in client.queries[0]["include_domains"]
    assert "greenhouse.io" in client.queries[0]["include_domains"]
    assert client.queries[0]["include_domains_mode"] == "prefer"


def test_search_only_stores_results_matching_requested_title_and_location(
    monkeypatch,
):
    client = FakeTavilyClient([
        {
            "title": "BDE Field Sales - Iwiz Android Robo",
            "url": "https://jobs.example.test/bde",
            "content": "Location: Chennai",
        },
        {
            "title": "React Developer - Example Corp",
            "url": "https://jobs.example.test/react-chennai",
            "content": "Location: Chennai",
        },
        {
            "title": "React Developer - Example Corp",
            "url": "https://jobs.example.test/react-hyderabad",
            "content": "Location: Hyderabad",
        },
        {
            "title": "React Developer - Example Labs",
            "url": "https://jobs.example.test/react-location-not-listed",
            "content": "Build frontend features with React and TypeScript.",
        },
        {
            "title": "React Developer - Example Corp",
            "url": "https://jobs.example.test/react-location-conflict",
            "location": "Chennai",
            "content": "Location: Hyderabad",
        },
        {
            "title": "Jobs Archives - Page 3 of 15 - KaaShiv InfoTech Blog",
            "url": (
                "https://www.kaashivinfotech.com/"
                "blog/category/jobs/page/3"
            ),
            "content": (
                "React Developer job openings in Hyderabad. "
                "Read our latest blog archive."
            ),
        },
    ])
    collection = FakeCollection()
    verified_urls = []
    monkeypatch.setattr(
        tavily_job_search_service,
        "verify_application_url",
        lambda url: (
            verified_urls.append(url)
            or {
                "valid": True,
                "job_verified": False,
                "verification_blocked": False,
            }
        ),
    )

    result = tavily_job_search_service.search_and_store_jobs(
        tavily_client=client,
        job_search_results_collection=collection,
        user_id="test-user",
        query="React Developer jobs in Hyderabad",
        job_title_query="React Developer",
        location_query="Hyderabad",
    )

    assert result["total_irrelevant_results"] == 4
    assert result["searches"][0]["irrelevant_result_count"] == 4
    assert result["total_non_job_results"] == 0
    assert [job["url"] for job in result["searches"][0]["saved_results"]] == [
        "https://jobs.example.test/react-hyderabad",
        "https://jobs.example.test/react-location-not-listed",
    ]
    assert verified_urls == [
        "https://jobs.example.test/react-hyderabad",
        "https://jobs.example.test/react-location-not-listed",
    ]
    assert collection.documents[0]["job_title_query"] == "React Developer"
    assert collection.documents[0]["location_query"] == "Hyderabad"
    assert collection.documents[1]["location"] is None
    assert collection.documents[1]["location_confirmed"] is False


def test_preference_search_filters_results_using_each_preference_pair(
    monkeypatch,
):
    client = FakeTavilyClient([
        {
            "title": "BDE Field Sales",
            "url": "https://jobs.example.test/bde",
            "content": "Location: Hyderabad",
        },
        {
            "title": "React Developer",
            "url": "https://jobs.example.test/react",
            "content": "Location: Hyderabad",
        },
    ])
    collection = FakeCollection()
    monkeypatch.setattr(
        tavily_job_search_service,
        "verify_application_url",
        lambda url: {
            "valid": True,
            "job_verified": False,
            "verification_blocked": False,
        },
    )

    result = tavily_job_search_service.search_and_store_jobs(
        tavily_client=client,
        job_search_results_collection=collection,
        user_id="test-user",
        preferences={
            "job_titles": ["React Developer"],
            "locations": ["Hyderabad"],
        },
    )

    assert result["total_irrelevant_results"] == 1
    assert [job["title"] for job in result["searches"][0]["saved_results"]] == [
        "React Developer"
    ]


def test_search_results_endpoint_hides_generic_and_mismatched_legacy_results(
    monkeypatch,
):
    from bson import ObjectId

    collection = FakeCollection([
        {
            "_id": ObjectId(),
            "user_id": "test-user",
            "title": "React Developer",
            "url": "https://jobs.example.test/react-hyderabad",
            "job_title_query": "React Developer",
            "location_query": "Hyderabad",
            "location": "Hyderabad",
            "content": "Location: Hyderabad",
            "created_at": 3,
        },
        {
            "_id": ObjectId(),
            "user_id": "test-user",
            "title": "BDE Field Sales",
            "url": "https://jobs.example.test/bde",
            "job_title_query": "custom",
            "location_query": "custom",
            "created_at": 2,
        },
        {
            "_id": ObjectId(),
            "user_id": "test-user",
            "title": "React Developer",
            "url": "https://jobs.example.test/react-chennai",
            "job_title_query": "React Developer",
            "location_query": "Hyderabad",
            "location": "Chennai",
            "content": "Location: Chennai",
            "created_at": 1,
        },
    ])
    monkeypatch.setattr(main, "job_search_results_collection", collection)

    result = main.get_my_search_results({"_id": "test-user"})

    assert result["total_results"] == 1
    assert result["results"][0]["title"] == "React Developer"


def test_job_posting_title_is_not_filtered_as_informational():
    assert not tavily_job_search_service._is_non_job_resource(
        "React Developer - Example Corp",
        "https://jobs.example.test/react-developer",
    )


def test_react_developer_search_matches_react_engineer_title():
    assert tavily_job_search_service._matches_requested_criteria(
        title="Frontend Engineer - React",
        content="Build user interfaces with React.",
        location="Hyderabad",
        job_title_query="React Developer",
        location_query="Hyderabad",
    )
    assert tavily_job_search_service._matches_requested_criteria(
        title="React Developer - Example Labs",
        content="Location not listed.",
        location=None,
        job_title_query="React Developer",
        location_query="Hyderabad",
    )
    assert not tavily_job_search_service._matches_requested_criteria(
        title="BDE Field Sales",
        content="Hiring now.",
        location="Hyderabad",
        job_title_query="React Developer",
        location_query="Hyderabad",
    )
    assert tavily_job_search_service._matches_requested_criteria(
        title="Frontend Engineer - Example Corp",
        content="Build user interfaces with React and TypeScript.",
        location="Hyderabad",
        job_title_query="React Developer",
        location_query="Hyderabad",
    )
    assert not tavily_job_search_service._matches_requested_criteria(
        title="Software Engineer - Example Corp",
        content="Build web applications with JavaScript.",
        location="Hyderabad",
        job_title_query="React Developer",
        location_query="Hyderabad",
    )


@pytest.mark.parametrize(
    ("query", "title", "content"),
    [
        ("React", "React Developer", "Build web applications."),
        (
            "React Developer",
            "Frontend Engineer",
            "Build applications using React and TypeScript.",
        ),
        ("frontend", "UI Developer", "User interface development."),
        ("backend", "Back-end Engineer", "Build REST services."),
        (
            "mern stack",
            "Full Stack Developer",
            "MongoDB, Express, React, and Node.js.",
        ),
    ],
)
def test_search_topics_accept_common_job_title_and_stack_variants(
    query,
    title,
    content,
):
    assert tavily_job_search_service._matches_requested_criteria(
        title=title,
        content=content,
        location="Hyderabad",
        job_title_query=query,
        location_query="Hyderabad",
    )


def test_search_query_includes_topic_variants_and_all_experience_levels():
    query = tavily_job_search_service._expand_job_search_query(
        "React Developer jobs in Hyderabad"
    ).lower()

    assert "react.js" in query
    assert "reactjs" in query
    assert "fresher" in query
    assert "entry level" in query
    assert "junior" in query
    assert "mid-level" in query
    assert "senior" in query
    assert "experienced" in query
    assert "do not limit by experience" in query


def test_search_keeps_results_across_experience_levels(monkeypatch):
    levels = ["Fresher", "1-3 years", "5+ years", "Senior"]
    client = FakeTavilyClient([
        {
            "title": f"React Developer - {level}",
            "url": f"https://jobs.example.test/react-{index}",
            "content": f"Location: Hyderabad\nExperience: {level}",
        }
        for index, level in enumerate(levels)
    ])
    collection = FakeCollection()
    monkeypatch.setattr(
        tavily_job_search_service,
        "verify_application_url",
        lambda url: {
            "valid": True,
            "job_verified": False,
            "verification_blocked": False,
        },
    )

    result = tavily_job_search_service.search_and_store_jobs(
        tavily_client=client,
        job_search_results_collection=collection,
        user_id="test-user",
        query="React Developer jobs in Hyderabad",
        job_title_query="React Developer",
        location_query="Hyderabad",
    )

    saved = result["searches"][0]["saved_results"]
    assert len(saved) == len(levels)
    assert {job["experience_required"] for job in saved} == set(levels)


def test_tutorial_results_are_filtered_by_title_and_path():
    assert tavily_job_search_service._is_non_job_resource(
        "React Tutorial",
        "https://example.test/react",
    )
    assert tavily_job_search_service._is_non_job_resource(
        "React",
        "https://example.test/docs/react",
    )
    assert tavily_job_search_service._is_non_job_resource(
        "Zensar Technologies Bengaluru Reviews",
        "https://www.ambitionbox.com/reviews/zensar-technologies-reviews/bengaluru-location",
    )
    assert not tavily_job_search_service._is_non_job_resource(
        "Software Engineer",
        "https://boards.greenhouse.io/example/jobs/123456",
    )
    assert tavily_job_search_service._is_non_job_resource(
        "Careers & Jobs/ Hiring Now",
        "https://www.linkedin.com/company/careers-jobs-hiring-now",
    )
    assert tavily_job_search_service._is_non_job_resource(
        "Jobs for Women in Hyderabad",
        "https://internshala.com/jobs-for-women/full-stack-developer-react-django-jobs-in-hyderabad",
    )
    assert tavily_job_search_service._is_non_job_resource(
        "Frank Jessel - BayWa re Solar Trade Global",
        "https://de.linkedin.com/in/frank-jessel-50708a11",
    )
    assert not tavily_job_search_service._is_non_job_resource(
        "Software Engineer",
        "https://www.linkedin.com/jobs/view/123456789",
    )


def test_linkedin_profile_cannot_be_approved_as_a_job_application():
    from fastapi import HTTPException

    with pytest.raises(HTTPException, match="not an individual job posting"):
        main.ensure_application_is_individual_job({
            "application_url": (
                "https://de.linkedin.com/in/frank-jessel-50708a11"
            ),
        })


def test_linkedin_profile_application_is_hidden_from_tracker(monkeypatch):
    user_id = "test-user"
    application = {
        "_id": "application-id",
        "user_id": user_id,
        "job_id": "job-id",
        "application_url": (
            "https://de.linkedin.com/in/frank-jessel-50708a11"
        ),
    }
    monkeypatch.setattr(
        main,
        "applications_collection",
        FakeCollection([application]),
    )
    monkeypatch.setattr(
        main,
        "jobs_collection",
        FakeCollection(),
    )

    result = main.get_applications({"_id": user_id})

    assert result["total_applications"] == 0
    assert result["applications"] == []


def test_listing_page_detection_rejects_search_pages_but_keeps_job_postings():
    assert tavily_job_search_service._is_listing_page(
        "50+ Data Cleaning Jobs, Employment 15 October",
        "https://pk.indeed.com/q-data-cleaning-jobs.html",
    )
    assert tavily_job_search_service._is_listing_page(
        "Software Engineer jobs",
        "https://www.linkedin.com/jobs/search/?keywords=engineer",
    )
    assert not tavily_job_search_service._is_listing_page(
        "Software Engineer",
        "https://www.linkedin.com/jobs/view/123456789",
    )
    assert not tavily_job_search_service._is_listing_page(
        "Backend Engineer",
        "https://boards.greenhouse.io/example/jobs/123456",
    )
    assert tavily_job_search_service._is_listing_page(
        "Working at Lamb Weston",
        "https://careers.lambweston.com/",
    )
    assert tavily_job_search_service._is_listing_page(
        "Search our Job Opportunities at Capital One",
        "https://www.capitalonecareers.com/search-jobs",
    )
    assert tavily_job_search_service._is_listing_page(
        "Current Openings",
        "https://jobs.cityoflancasterpa.gov/current-openings.aspx",
    )
    assert tavily_job_search_service._is_listing_page(
        "Careers at KPFF Consulting Engineers",
        "https://careers.smartrecruiters.com/KPFFConsultingEngineers",
    )
    assert not tavily_job_search_service._is_listing_page(
        "BDE – Immediate Hiring",
        "https://apna.co/job/chennai-region/bde-immediate-hiring-892079897",
    )
    assert tavily_job_search_service._is_listing_page(
        "Amazon",
        "https://www.amazon.com/",
    )


def test_informational_archive_and_social_results_are_filtered():
    assert tavily_job_search_service._is_non_job_resource(
        "Jobs Archives - Page 3 of 15 - KaaShiv InfoTech Blog",
        "https://www.kaashivinfotech.com/blog/category/jobs/page/3",
    )
    assert tavily_job_search_service._is_non_job_resource(
        "Instagram",
        "https://www.instagram.com/p/DY46iqwAXUf",
    )
    assert tavily_job_search_service._is_non_job_resource(
        "React Developer Jobs - New Jobs Daily - Start Applying Now",
        "https://www.bing.com/aclick?u=redirect",
    )


def test_search_skips_job_board_listing_pages_before_storage(
    monkeypatch,
):
    client = FakeTavilyClient([
        {
            "title": "50+ Data Cleaning Jobs, Employment 15 October",
            "url": "https://pk.indeed.com/q-data-cleaning-jobs.html",
        },
    ])
    collection = object()

    def fail_if_verified(url):
        raise AssertionError(f"Listing URL should not be verified: {url}")

    monkeypatch.setattr(
        tavily_job_search_service,
        "verify_application_url",
        fail_if_verified,
    )

    result = tavily_job_search_service.search_and_store_jobs(
        tavily_client=client,
        job_search_results_collection=collection,
        user_id="test-user",
        query="Backend Engineer jobs in Toronto",
    )

    assert result["total_non_job_results"] == 1
    assert result["total_saved"] == 0
    assert result["searches"][0]["saved_results"] == []


def test_search_persists_manual_review_results_without_marking_them_verified(
    monkeypatch,
):
    collection = FakeCollection()
    client = FakeTavilyClient([
        {
            "title": "Software Engineer",
            "url": "https://unlisted-jobs.example.test/software-engineer",
            "content": "Company: Example Corp\nLocation: Toronto",
        },
    ])
    monkeypatch.setattr(
        tavily_job_search_service,
        "verify_application_url",
        lambda url: {
            "valid": False,
            "job_verified": False,
            "verification_blocked": True,
            "message": f"The domain for {url} needs manual review.",
        },
    )

    result = tavily_job_search_service.search_and_store_jobs(
        tavily_client=client,
        job_search_results_collection=collection,
        user_id="test-user",
        query="Software Engineer jobs in Toronto",
        job_title_query="Software Engineer",
        location_query="Toronto",
    )

    stored = collection.documents[0]
    manual_result = result["searches"][0]["manual_review_results"][0]

    assert result["total_saved"] == 0
    assert result["total_manual_review_saved"] == 1
    assert len(collection.documents) == 1
    assert stored["url_verified"] is False
    assert stored["verification_status"] == "manual_review_required"
    assert manual_result["url_verified"] is False
    assert manual_result["search_result_id"] == str(stored["_id"])

    monkeypatch.setattr(main, "job_search_results_collection", collection)
    visible_results = main.get_my_search_results({"_id": "test-user"})
    assert visible_results["total_results"] == 1
    assert visible_results["results"][0]["url_verified"] is False
    assert visible_results["results"][0]["verification_status"] == (
        "manual_review_required"
    )


def test_manual_review_results_are_deduplicated(monkeypatch):
    collection = FakeCollection()
    client = FakeTavilyClient([
        {
            "title": "Software Engineer",
            "url": "https://unlisted-jobs.example.test/software-engineer",
        },
    ])

    verification = {"valid": False}

    def get_verification(url):
        return {
            "valid": verification["valid"],
            "job_verified": False,
            "verification_blocked": not verification["valid"],
            "message": f"The domain for {url} needs manual review.",
        }

    monkeypatch.setattr(
        tavily_job_search_service,
        "verify_application_url",
        get_verification,
    )
    first_result = tavily_job_search_service.search_and_store_jobs(
        tavily_client=client,
        job_search_results_collection=collection,
        user_id="test-user",
        query="Software Engineer jobs",
    )
    assert first_result["total_manual_review_saved"] == 1

    duplicate_result = tavily_job_search_service.search_and_store_jobs(
        tavily_client=client,
        job_search_results_collection=collection,
        user_id="test-user",
        query="Software Engineer jobs",
    )
    assert duplicate_result["total_manual_review_saved"] == 0
    assert len(collection.documents) == 1

    verification["valid"] = True
    promoted_result = tavily_job_search_service.search_and_store_jobs(
        tavily_client=client,
        job_search_results_collection=collection,
        user_id="test-user",
        query="Software Engineer jobs",
    )

    assert collection.documents[0]["url_verified"] is True
    assert promoted_result["searches"][0]["duplicates"][0][
        "url_verified"
    ] is True
