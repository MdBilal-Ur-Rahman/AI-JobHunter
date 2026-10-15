def get_user_preferences(
    preferences_collection,
    user_id: str
):
    """
    Get saved job preferences for a user.

    This service only reads the user's preferences.
    It does not handle authentication or FastAPI routes.
    """

    if not user_id:
        raise ValueError(
            "user_id is required"
        )

    preferences = preferences_collection.find_one(
        {
            "user_id": str(user_id)
        },
        {
            "_id": 0
        }
    )

    if not preferences:
        return None

    return preferences