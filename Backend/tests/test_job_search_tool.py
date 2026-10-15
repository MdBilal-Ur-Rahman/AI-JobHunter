import sys
from types import ModuleType, SimpleNamespace

import pytest

from app.tools import job_search_tool


def test_job_search_uses_authenticated_context_user_id(monkeypatch):
    stored_preferences = object()
    fake_main = ModuleType("app.main")
    fake_main.db = {"preferences": stored_preferences}
    fake_main.job_search_results_collection = object()
    fake_main.tavily_client = object()
    monkeypatch.setitem(sys.modules, "app.main", fake_main)

    preferences_lookups = []
    monkeypatch.setattr(
        job_search_tool,
        "get_user_preferences",
        lambda preferences_collection, user_id: (
            preferences_lookups.append((preferences_collection, user_id))
            or {
                "job_titles": ["Data Analyst"],
                "locations": ["Remote"],
            }
        ),
    )

    search_calls = []
    monkeypatch.setattr(
        job_search_tool,
        "search_and_store_jobs",
        lambda **kwargs: search_calls.append(kwargs) or {"count": 1},
    )

    result = job_search_tool.search_jobs.func(
        {
            "user_id": "untrusted-user",
            "job_titles": [],
            "locations": [],
        },
        runtime=SimpleNamespace(
            context={"user_id": "authenticated-user"}
        ),
    )

    assert result == {"count": 1}
    assert preferences_lookups == [
        (stored_preferences, "authenticated-user")
    ]
    assert search_calls[0]["user_id"] == "authenticated-user"
    assert search_calls[0]["preferences"] == {
        "user_id": "authenticated-user",
        "job_titles": ["Data Analyst"],
        "locations": ["Remote"],
    }
    assert set(job_search_tool.search_jobs.args) == {"preferences"}


def test_job_search_requires_authenticated_context():
    with pytest.raises(ValueError, match="Authenticated user context"):
        job_search_tool.search_jobs.func(
            {"job_titles": ["Developer"], "locations": ["Remote"]},
            runtime=SimpleNamespace(context={}),
        )
