from datetime import datetime, timezone
from getpass import getpass
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from pymongo import MongoClient

from app.services.password_service import (
    MAX_BCRYPT_PASSWORD_BYTES,
    hash_password,
)


LOCAL_MONGO_HOSTS = {"localhost", "127.0.0.1", "::1"}
DATABASE_NAME = "ai-jobhunter"


def get_local_mongo_uri() -> str:
    mongo_uri = os.getenv("MONGO_URI", "").strip()
    if not mongo_uri:
        raise RuntimeError("MONGO_URI is not configured in Backend/.env.")

    parsed_uri = urlparse(mongo_uri)
    if (
        parsed_uri.scheme != "mongodb"
        or parsed_uri.hostname not in LOCAL_MONGO_HOSTS
    ):
        raise RuntimeError(
            "This recovery command only works with a local MongoDB "
            "(localhost, 127.0.0.1, or ::1). Remote MongoDB is refused."
        )

    return mongo_uri


def validate_new_password(password: str, confirmation: str) -> None:
    if password != confirmation:
        raise ValueError("Passwords do not match.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be no more than "
            f"{MAX_BCRYPT_PASSWORD_BYTES} UTF-8 bytes."
        )


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent / ".env")

    mongo_uri = get_local_mongo_uri()

    email = input("Account email: ").strip().lower()
    if not email:
        raise ValueError("Email cannot be empty.")

    password = getpass("New password (hidden): ")
    confirmation = getpass("Confirm new password (hidden): ")
    validate_new_password(password, confirmation)

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
    try:
        client.admin.command("ping")
        database = client[DATABASE_NAME]
        result = database.users.update_one(
            {"email": email},
            {
                "$set": {
                    "password": hash_password(password),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        if result.matched_count == 0:
            raise LookupError(
                "No account with that email exists in the local database."
            )

        user_id = str(database.users.find_one(
            {"email": email},
            {"_id": 1},
        )["_id"])
        database.active_sessions.delete_many({"user_id": user_id})
        database.password_reset_tokens.delete_many({"user_id": user_id})
    finally:
        client.close()

    print("Local account password reset successfully. You can log in now.")


if __name__ == "__main__":
    main()
