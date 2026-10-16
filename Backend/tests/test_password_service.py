import pytest

from app.services.password_service import (
    MAX_BCRYPT_PASSWORD_BYTES,
    hash_password,
    password_within_bcrypt_limit,
    verify_password,
)


def test_password_hash_can_be_verified():
    password = "correct horse battery staple"

    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("incorrect password", password_hash)


def test_bcrypt_password_limit_counts_utf8_bytes():
    assert password_within_bcrypt_limit("a" * MAX_BCRYPT_PASSWORD_BYTES)
    assert not password_within_bcrypt_limit(
        "a" * (MAX_BCRYPT_PASSWORD_BYTES + 1)
    )
    assert not password_within_bcrypt_limit("é" * 37)


def test_hashing_does_not_truncate_long_passwords():
    password = "a" * (MAX_BCRYPT_PASSWORD_BYTES + 1)

    with pytest.raises(ValueError):
        hash_password(password)


def test_verification_surfaces_malformed_stored_hash():
    with pytest.raises(ValueError):
        verify_password("any password", "not-a-bcrypt-hash")
