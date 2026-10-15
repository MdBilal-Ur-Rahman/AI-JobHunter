import math
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from pymongo.errors import DuplicateKeyError

from app.services.url_verification_service import (
    verify_application_url,
)


# =========================================================
# CONFIGURATION
# =========================================================

MAX_TITLE_LENGTH = 500
MAX_COMPANY_LENGTH = 150
MAX_LOCATION_LENGTH = 150
MAX_CONTENT_SCAN_LENGTH = 5000
MAX_SALARY_LENGTH = 150
MAX_EXPERIENCE_LENGTH = 100
MAX_EMPLOYMENT_TYPE_LENGTH = 100
MAX_TAVILY_ID_LENGTH = 200

TRACKING_QUERY_PARAMETERS = {
    "gclid",
    "fbclid",
    "msclkid",
    "ref",
    "source",
    "campaign",
    "tracking",
}


# =========================================================
# SAFE HELPERS
# =========================================================

def _verification_failure(
    message: str,
    *,
    blocked: bool = True,
) -> dict:
    return {
        "valid": False,
        "job_verified": False,
        "verification_blocked": blocked,
        "requested_url": None,
        "final_url": None,
        "hostname": None,
        "trusted_domain": None,
        "message": message,
        "error": message,
    }


def _safe_text(
    value,
    default: str = "",
    max_length: int | None = None,
) -> str:
    if not isinstance(value, str):
        value = default

    value = value.strip()

    if max_length is not None:
        value = value[:max_length]

    return value


def _safe_score(value):
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        if math.isfinite(value):
            return value

    return None


def _normalize_url_for_comparison(
    url: str,
) -> str | None:
    """
    Normalize URLs for duplicate comparison only.
    This function does not establish URL safety.
    """
    if not isinstance(url, str) or not url.strip():
        return None

    try:
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower()

        if scheme not in {"http", "https"}:
            return None

        if not parsed.hostname:
            return None

        if parsed.username or parsed.password:
            return None

        hostname = parsed.hostname.lower().rstrip(".")

        if not hostname:
            return None

        port = parsed.port

        if ":" in hostname and not hostname.startswith("["):
            hostname = f"[{hostname}]"

        netloc = hostname

        if port is not None:
            if not (
                (scheme == "http" and port == 80)
                or (scheme == "https" and port == 443)
            ):
                netloc = f"{netloc}:{port}"

        path = parsed.path or "/"

        if path != "/":
            path = path.rstrip("/") or "/"

        query_parameters = []

        for key, value in parse_qsl(
            parsed.query,
            keep_blank_values=True,
        ):
            if key.lower().startswith("utm_"):
                continue

            if key.lower() in TRACKING_QUERY_PARAMETERS:
                continue

            query_parameters.append((key, value))

        query_parameters.sort()

        normalized_query = urlencode(
            query_parameters,
            doseq=True,
        )

        return urlunparse(
            (
                scheme,
                netloc,
                path,
                "",
                normalized_query,
                "",
            )
        )

    except (ValueError, TypeError):
        return None


def _extract_company(
    title: str,
    content: str,
) -> str | None:
    text = f"{title}\n{content[:MAX_CONTENT_SCAN_LENGTH]}"

    patterns = [
        r"(?im)^\s*company\s*:\s*([^\n|]{2,150})",
        r"(?im)^\s*employer\s*:\s*([^\n|]{2,150})",
        r"(?im)^\s*organization\s*:\s*([^\n|]{2,150})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            value = match.group(1).strip(" \t-–—|")

            if value:
                return value[:MAX_COMPANY_LENGTH]

    return None


def _extract_location(
    content: str,
) -> str | None:
    patterns = [
        r"(?im)^\s*(?:job\s+)?location\s*:\s*([^\n|]{2,150})",
        r"(?im)^\s*job\s+located\s+in\s*:\s*([^\n|]{2,150})",
        r"(?im)^\s*location\s*-\s*([^\n|]{2,150})",
    ]

    content = content[:MAX_CONTENT_SCAN_LENGTH]

    for pattern in patterns:
        match = re.search(pattern, content)

        if match:
            value = match.group(1).strip(" \t-–—|")

            if value:
                return value[:MAX_LOCATION_LENGTH]

    return None


def _extract_employment_type(
    content: str,
) -> str | None:
    match = re.search(
        r"(?im)^\s*(?:employment\s+type|job\s+type)\s*:\s*([^\n|]{2,100})",
        content[:MAX_CONTENT_SCAN_LENGTH],
    )

    if match:
        value = match.group(1).strip(" \t-–—|")

        if value:
            return value[:MAX_EMPLOYMENT_TYPE_LENGTH]

    return None


def _extract_salary(
    content: str,
) -> str | None:
    match = re.search(
        r"(?im)^\s*(?:salary|compensation|pay\s+range)\s*:\s*([^\n|]{2,150})",
        content[:MAX_CONTENT_SCAN_LENGTH],
    )

    if match:
        value = match.group(1).strip(" \t-–—|")

        if value:
            return value[:MAX_SALARY_LENGTH]

    return None


def _extract_experience(
    content: str,
) -> str | None:
    match = re.search(
        r"(?im)^\s*(?:experience|required\s+experience)\s*:\s*([^\n|]{2,100})",
        content[:MAX_CONTENT_SCAN_LENGTH],
    )

    if match:
        value = match.group(1).strip(" \t-–—|")

        if value:
            return value[:MAX_EXPERIENCE_LENGTH]

    return None


def _is_listing_page(
    title: str,
    url: str,
) -> bool:
    """
    Heuristic only. Not proof of job authenticity.
    """
    parsed = urlparse(url)
    path = (parsed.path or "").lower()
    title_lower = title.lower()

    listing_path_patterns = [
        r"/jobs/?$",
        r"/jobs-in-[^/]+/?$",
        r"/job-search/?$",
        r"/search/jobs/?$",
        r"/vacancies/?$",
        r"/job-openings/?$",
        r"/careers/?$",
        r"/role/l/?$",
    ]

    for pattern in listing_path_patterns:
        if re.search(pattern, path):
            return True

    listing_title_patterns = [
        r"\bjob vacancies\b",
        r"\bjob openings\b",
        r"\bjobs in\b",
        r"\bsearch results\b",
        r"\bopen roles\b",
        r"\bjob listings\b",
    ]

    return any(
        re.search(pattern, title_lower)
        for pattern in listing_title_patterns
    )


def _find_existing_result(
    collection,
    user_id: str,
    url: str,
):
    """
    Find an existing raw result owned by this user.
    """
    existing = collection.find_one({
        "user_id": user_id,
        "url": url,
    })

    if existing:
        return existing

    normalized_candidate = _normalize_url_for_comparison(url)

    if not normalized_candidate:
        return None

    cursor = collection.find(
        {"user_id": user_id},
        {
            "_id": 1,
            "url": 1,
            "title": 1,
            "content": 1,
            "company": 1,
            "location": 1,
            "employment_type": 1,
            "salary": 1,
            "experience_required": 1,
            "source_domain": 1,
            "url_verified": 1,
            "job_verified": 1,
            "verification_status": 1,
        },
    ).limit(500)

    for document in cursor:
        normalized_stored = _normalize_url_for_comparison(
            document.get("url", "")
        )

        if (
            normalized_stored
            and normalized_stored == normalized_candidate
        ):
            return document

    return None


def _summarize_duplicate(
    url: str,
    title: str,
    existing_result: dict,
) -> dict:
    """
    Return the existing raw record ID for downstream processing.
    """
    existing_id = existing_result.get("_id")

    existing_id_text = (
        str(existing_id)
        if existing_id is not None
        else None
    )

    return {
        "url": existing_result.get("url") or url,
        "title": existing_result.get("title") or title,
        "company": existing_result.get("company"),
        "location": existing_result.get("location"),
        "content": existing_result.get("content", ""),
        "employment_type": existing_result.get("employment_type"),
        "salary": existing_result.get("salary"),
        "experience_required": existing_result.get(
            "experience_required"
        ),
        "source_domain": existing_result.get("source_domain"),
        "url_verified": existing_result.get("url_verified") is True,
        "job_verified": existing_result.get("job_verified") is True,
        "verification_status": existing_result.get(
            "verification_status"
        ),
        "search_result_id": existing_id_text,
        "existing_search_result_id": existing_id_text,
        "is_duplicate": True,
        "duplicate_url": url,
    }


# =========================================================
# MAIN SEARCH AND STORE FUNCTION
# =========================================================

def search_and_store_jobs(
    tavily_client,
    job_search_results_collection,
    user_id: str,
    preferences: dict | None = None,
    query: str | None = None,
    max_job_content_length: int = 100_000,
    max_results_per_user: int = 100,
):
    """
    Search Tavily and store URL-validated raw search results.

    URL validation does not establish that a job is authentic.
    This function does not submit job applications.
    """

    # -----------------------------------------------------
    # 1. Validate input
    # -----------------------------------------------------

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id is required")

    user_id = user_id.strip()

    if preferences is None:
        preferences = {}

    if not isinstance(preferences, dict):
        raise ValueError("preferences must be a dictionary")

    if (
        isinstance(max_job_content_length, bool)
        or not isinstance(max_job_content_length, int)
        or max_job_content_length < 0
    ):
        raise ValueError(
            "max_job_content_length must be a non-negative integer"
        )

    if (
        isinstance(max_results_per_user, bool)
        or not isinstance(max_results_per_user, int)
        or max_results_per_user < 1
    ):
        raise ValueError(
            "max_results_per_user must be a positive integer"
        )

    # -----------------------------------------------------
    # 2. Prepare queries
    # -----------------------------------------------------

    if query is not None:
        if not isinstance(query, str):
            raise ValueError("Search query must be a string")

        query = query.strip()

        if not query:
            raise ValueError("Search query cannot be empty")

        searches_to_run = [{
            "query": query,
            "job_title": "custom",
            "location": "custom",
        }]

    else:
        job_titles = preferences.get("job_titles", [])
        locations = preferences.get("locations", [])

        if not isinstance(job_titles, list) or not job_titles:
            raise ValueError("At least one job title is required")

        if not isinstance(locations, list) or not locations:
            raise ValueError("At least one location is required")

        searches_to_run = []

        for job_title in job_titles:
            for location in locations:
                if (
                    not isinstance(job_title, str)
                    or not job_title.strip()
                    or not isinstance(location, str)
                    or not location.strip()
                ):
                    continue

                clean_title = job_title.strip()
                clean_location = location.strip()

                searches_to_run.append({
                    "query": (
                        f"{clean_title} jobs in {clean_location}"
                    ),
                    "job_title": clean_title,
                    "location": clean_location,
                })

        if not searches_to_run:
            raise ValueError(
                "No valid job title and location combinations "
                "were provided"
            )

    # -----------------------------------------------------
    # 3. Counters
    # -----------------------------------------------------

    searches = []
    total_saved = 0
    total_duplicates = 0
    total_invalid_urls = 0
    total_verification_blocked = 0
    total_deleted_old_results = 0
    total_search_errors = 0
    total_storage_errors = 0

    # -----------------------------------------------------
    # 4. Execute searches
    # -----------------------------------------------------

    for search_item in searches_to_run:
        search_query = search_item["query"]
        job_title = search_item["job_title"]
        location = search_item["location"]

        saved_results = []
        duplicate_results = []
        invalid_url_results = []
        verification_blocked_urls = []

        deleted_old_results = 0
        tavily_results = []

        try:
            response = tavily_client.search(
                query=search_query,
                search_depth="basic",
                max_results=10,
            )

            if not isinstance(response, dict):
                raise ValueError("Unexpected response from Tavily")

            tavily_results = response.get("results", [])

            if not isinstance(tavily_results, list):
                raise ValueError("Tavily results must be a list")

        except Exception:
            total_search_errors += 1

            searches.append({
                "query": search_query,
                "tavily_results_count": 0,
                "saved_count": 0,
                "available_count": 0,
                "newly_saved_count": 0,
                "duplicate_count": 0,
                "invalid_url_count": 0,
                "verification_blocked_count": 0,
                "deleted_old_results": 0,
                "saved_results": [],
                "duplicates": [],
                "invalid_urls": [],
                "verification_blocked_urls": [],
                "error": "Tavily search failed",
            })

            continue

        # -------------------------------------------------
        # 5. Process results
        # -------------------------------------------------

        for item in tavily_results:
            if not isinstance(item, dict):
                continue

            title = (
                _safe_text(
                    item.get("title"),
                    default="Untitled job result",
                    max_length=MAX_TITLE_LENGTH,
                )
                or "Untitled job result"
            )

            content = _safe_text(
                item.get("content"),
                default="",
                max_length=max_job_content_length,
            )

            raw_url = item.get("url")

            if not isinstance(raw_url, str) or not raw_url.strip():
                invalid_url_results.append({
                    "url": None,
                    "title": title,
                    "verification": _verification_failure(
                        "Application URL is missing.",
                        blocked=False,
                    ),
                })

                total_invalid_urls += 1
                continue

            url = raw_url.strip()

            # ---------------------------------------------
            # 6. Basic URL validation
            # ---------------------------------------------

            try:
                parsed_url = urlparse(url)

                valid_syntax = (
                    parsed_url.scheme.lower() in {"http", "https"}
                    and bool(parsed_url.hostname)
                    and not parsed_url.username
                    and not parsed_url.password
                )

                # Accessing .port also detects malformed ports.
                if valid_syntax:
                    _ = parsed_url.port

            except (ValueError, TypeError):
                valid_syntax = False
                parsed_url = None

            if not valid_syntax or parsed_url is None:
                invalid_url_results.append({
                    "url": url,
                    "title": title,
                    "verification": _verification_failure(
                        "URL syntax or scheme is not allowed.",
                        blocked=False,
                    ),
                })

                total_invalid_urls += 1
                continue

            # ---------------------------------------------
            # 7. Verify URL
            # ---------------------------------------------

            try:
                verification_result = verify_application_url(url)

                if not isinstance(verification_result, dict):
                    verification_result = _verification_failure(
                        "Unexpected URL verification response."
                    )

            except Exception:
                verification_result = _verification_failure(
                    "Application URL verification failed."
                )

            if verification_result.get("valid") is not True:
                if (
                    verification_result.get(
                        "verification_blocked"
                    ) is True
                ):
                    verification_blocked_urls.append({
                        "url": url,
                        "title": title,
                        "status": "manual_review_required",
                        "message": (
                            "Automated URL verification could not "
                            "approve this destination."
                        ),
                        "verification": verification_result,
                    })

                    total_verification_blocked += 1

                else:
                    invalid_url_results.append({
                        "url": url,
                        "title": title,
                        "verification": verification_result,
                    })

                    total_invalid_urls += 1

                continue

            # ---------------------------------------------
            # 8. Check for existing raw result
            # ---------------------------------------------

            try:
                existing_result = _find_existing_result(
                    job_search_results_collection,
                    user_id,
                    url,
                )

            except Exception:
                total_storage_errors += 1
                continue

            if existing_result:
                duplicate_summary = _summarize_duplicate(
                    url,
                    title,
                    existing_result,
                )

                duplicate_results.append(duplicate_summary)

                if duplicate_summary.get("search_result_id"):
                    saved_results.append(duplicate_summary)

                total_duplicates += 1
                continue

            # ---------------------------------------------
            # 9. Extract labelled details
            # ---------------------------------------------

            company = _extract_company(title, content)
            extracted_location = _extract_location(content)
            employment_type = _extract_employment_type(content)
            salary = _extract_salary(content)
            experience = _extract_experience(content)

            source_domain = (
                parsed_url.hostname.lower().rstrip(".")
            )

            # ---------------------------------------------
            # 10. Prepare raw result document
            # ---------------------------------------------

            now = datetime.now(timezone.utc)

            search_result_data = {
                "user_id": user_id,
                "search_query": search_query,
                "job_title_query": job_title,
                "location_query": location,
                "url": url,
                "original_url": url,
                "normalized_url": (
                    _normalize_url_for_comparison(url)
                ),
                "title": title,
                "content": content,
                "company": company,
                "location": extracted_location or (
                    location if location != "custom" else None
                ),
                "employment_type": employment_type,
                "salary": salary,
                "experience_required": experience,
                "source_domain": source_domain,
                "tavily_score": _safe_score(item.get("score")),
                "tavily_result_id": _safe_text(
                    item.get("id"),
                    max_length=MAX_TAVILY_ID_LENGTH,
                ),
                "source": "tavily",
                "result_type": "raw_search_result",
                "url_verified": True,
                "job_verified": False,
                "verification_status": (
                    "url_validated_job_unverified"
                ),
                "url_verification": verification_result,
                "created_at": now,
            }

            # ---------------------------------------------
            # 11. Enforce per-user storage limit
            # ---------------------------------------------

            try:
                current_result_count = (
                    job_search_results_collection.count_documents({
                        "user_id": user_id
                    })
                )

                oldest_result = None

                if current_result_count >= max_results_per_user:
                    oldest_result = (
                        job_search_results_collection.find_one(
                            {"user_id": user_id},
                            sort=[("created_at", 1)],
                        )
                    )

                    if oldest_result is None:
                        total_storage_errors += 1
                        continue

                    # Delete the oldest result first to enforce
                    # the limit. Restore it if insertion fails.
                    delete_result = (
                        job_search_results_collection.delete_one({
                            "_id": oldest_result["_id"],
                            "user_id": user_id,
                        })
                    )

                    if delete_result.deleted_count == 0:
                        total_storage_errors += 1
                        continue

                try:
                    insert_result = (
                        job_search_results_collection.insert_one(
                            search_result_data
                        )
                    )

                except Exception:
                    # Restore the old record if possible.
                    if oldest_result is not None:
                        try:
                            job_search_results_collection.insert_one(
                                oldest_result
                            )
                        except Exception:
                            pass

                    raise

                if oldest_result is not None:
                    deleted_old_results += 1
                    total_deleted_old_results += 1

            except DuplicateKeyError:
                try:
                    existing_result = _find_existing_result(
                        job_search_results_collection,
                        user_id,
                        url,
                    )

                except Exception:
                    existing_result = None

                if existing_result:
                    duplicate_summary = _summarize_duplicate(
                        url,
                        title,
                        existing_result,
                    )

                    duplicate_results.append(duplicate_summary)

                    if duplicate_summary.get("search_result_id"):
                        saved_results.append(duplicate_summary)

                    total_duplicates += 1

                else:
                    total_storage_errors += 1

                continue

            except Exception:
                total_storage_errors += 1
                continue

            # ---------------------------------------------
            # 12. Return newly stored result
            # ---------------------------------------------

            saved_results.append({
                "search_result_id": str(
                    insert_result.inserted_id
                ),
                "url": url,
                "title": title,
                "company": company,
                "location": search_result_data["location"],
                "content": content,
                "employment_type": employment_type,
                "salary": salary,
                "experience_required": experience,
                "source_domain": source_domain,
                "url_verified": True,
                "job_verified": False,
                "verification_status": (
                    "url_validated_job_unverified"
                ),
                "is_duplicate": False,
            })

            total_saved += 1

        # -------------------------------------------------
        # 13. Per-query summary
        # -------------------------------------------------

        newly_saved_count = sum(
            1
            for result in saved_results
            if not result.get("is_duplicate", False)
        )

        searches.append({
            "query": search_query,
            "tavily_results_count": len(tavily_results),
            "saved_count": newly_saved_count,
            "available_count": len(saved_results),
            "newly_saved_count": newly_saved_count,
            "duplicate_count": len(duplicate_results),
            "invalid_url_count": len(invalid_url_results),
            "verification_blocked_count": len(
                verification_blocked_urls
            ),
            "deleted_old_results": deleted_old_results,
            "saved_results": saved_results,
            "duplicates": duplicate_results,
            "invalid_urls": invalid_url_results,
            "verification_blocked_urls": (
                verification_blocked_urls
            ),
            "error": None,
        })

    # -----------------------------------------------------
    # 14. Final response
    # -----------------------------------------------------

    return {
        "message": "Tavily job search completed",
        "total_queries": len(searches),
        "total_saved": total_saved,
        "total_duplicates": total_duplicates,
        "total_invalid_urls": total_invalid_urls,
        "total_verification_blocked": (
            total_verification_blocked
        ),
        "total_deleted_old_results": (
            total_deleted_old_results
        ),
        "total_search_errors": total_search_errors,
        "total_storage_errors": total_storage_errors,
        "searches": searches,
    }