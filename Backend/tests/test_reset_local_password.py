import pytest

from reset_local_password import (
    get_local_mongo_uri,
    validate_new_password,
)


@pytest.mark.parametrize(
    "uri",
    [
        "mongodb://localhost:27017",
        "mongodb://127.0.0.1:27017/ai-jobhunter",
        "mongodb://[::1]:27017/ai-jobhunter",
    ],
)
def test_local_recovery_accepts_local_mongodb_only(monkeypatch, uri):
    monkeypatch.setenv("MONGO_URI", uri)

    assert get_local_mongo_uri() == uri


@pytest.mark.parametrize(
    "uri",
    [
        "mongodb+srv://cluster.example.test",
        "mongodb://192.168.1.15:27017",
    ],
)
def test_local_recovery_refuses_remote_mongodb(monkeypatch, uri):
    monkeypatch.setenv("MONGO_URI", uri)

    with pytest.raises(RuntimeError, match="local MongoDB"):
        get_local_mongo_uri()


def test_new_password_validation_matches_bcrypt_limits():
    validate_new_password("a" * 72, "a" * 72)

    with pytest.raises(ValueError, match="at least 8"):
        validate_new_password("short", "short")

    with pytest.raises(ValueError, match="do not match"):
        validate_new_password("correct-password", "different-password")

    with pytest.raises(ValueError, match="72 UTF-8 bytes"):
        validate_new_password("a" * 73, "a" * 73)
