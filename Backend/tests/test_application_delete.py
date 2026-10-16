from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app import main


class FakeApplicationsCollection:
    def __init__(self, documents):
        self.documents = list(documents)

    def delete_one(self, query):
        for index, document in enumerate(self.documents):
            if all(document.get(key) == value for key, value in query.items()):
                del self.documents[index]
                return SimpleNamespace(deleted_count=1)

        return SimpleNamespace(deleted_count=0)


def test_delete_application_removes_only_current_users_record(monkeypatch):
    application_id = ObjectId()
    collection = FakeApplicationsCollection([
        {"_id": application_id, "user_id": "current-user"},
        {"_id": ObjectId(), "user_id": "another-user"},
    ])
    monkeypatch.setattr(main, "applications_collection", collection)

    result = main.delete_application(
        str(application_id),
        {"_id": "current-user"},
    )

    assert result == {
        "message": "Application deleted successfully",
        "application_id": str(application_id),
    }
    assert len(collection.documents) == 1
    assert collection.documents[0]["user_id"] == "another-user"


def test_delete_application_rejects_invalid_id(monkeypatch):
    collection = FakeApplicationsCollection([])
    monkeypatch.setattr(main, "applications_collection", collection)

    with pytest.raises(HTTPException) as error:
        main.delete_application("invalid-id", {"_id": "current-user"})

    assert error.value.status_code == 400
    assert error.value.detail == "Invalid application ID"


def test_delete_application_returns_not_found_for_other_users_record(
    monkeypatch,
):
    application_id = ObjectId()
    collection = FakeApplicationsCollection([
        {"_id": application_id, "user_id": "another-user"},
    ])
    monkeypatch.setattr(main, "applications_collection", collection)

    with pytest.raises(HTTPException) as error:
        main.delete_application(
            str(application_id),
            {"_id": "current-user"},
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Application not found"
    assert len(collection.documents) == 1
