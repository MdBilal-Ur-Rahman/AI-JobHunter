from typing import TypedDict

from langchain.tools import ToolRuntime, tool

from app.services.tavily_job_search_service import (
    search_and_store_jobs
)

from app.services.user_preferences_service import (
    get_user_preferences
)

class JobAgentContext(TypedDict):
    user_id: str


@tool
def search_jobs(
    preferences: dict,
    runtime: ToolRuntime[JobAgentContext],
) -> dict:
    """
    Search for jobs using the user's job preferences.

    This LangChain tool uses the existing Tavily job-search service.

    If job titles or locations are missing, saved user preferences
    are used when available.
    """

    if not isinstance(preferences, dict):
        raise ValueError(
            "preferences must be a dictionary"
        )

    user_id = runtime.context.get("user_id")

    if not user_id:
        raise ValueError(
            "Authenticated user context is required"
        )

    from app.main import (
        db,
        job_search_results_collection,
        tavily_client,
    )

    saved_preferences = get_user_preferences(
        preferences_collection=db["preferences"],
        user_id=str(user_id)
    )

    job_titles = preferences.get(
        "job_titles"
    )

    locations = preferences.get(
        "locations"
    )

    if not job_titles and saved_preferences:
        job_titles = saved_preferences.get(
            "job_titles",
            []
        )

    if not locations and saved_preferences:
        locations = saved_preferences.get(
            "locations",
            []
        )

    search_preferences = {
        **preferences,
        "user_id": str(user_id),
        "job_titles": job_titles or [],
        "locations": locations or []
    }

    if not search_preferences["job_titles"]:
        raise ValueError(
            "No job titles provided and no saved job titles found"
        )

    if not search_preferences["locations"]:
        raise ValueError(
            "No locations provided and no saved locations found"
        )

    # =========================================================
    # SAFETY VALIDATION
    # Ensure job titles and locations are provided as lists.
    # This prevents invalid input from reaching the search service.
    # =========================================================

    if not isinstance(
        search_preferences["job_titles"],
        list
    ):
        raise ValueError(
            "job_titles must be a list"
        )

    if not isinstance(
        search_preferences["locations"],
        list
    ):
        raise ValueError(
            "locations must be a list"
        )

    return search_and_store_jobs(
        tavily_client=tavily_client,
        job_search_results_collection=job_search_results_collection,
        user_id=str(user_id),
        preferences=search_preferences
    )