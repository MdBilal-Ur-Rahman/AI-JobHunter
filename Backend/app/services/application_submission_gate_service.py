from typing import Any, Dict


def check_submission_gate(
    application: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Check whether an application is allowed to proceed
    to the final human confirmation stage.

    Safety rules:
    - Application must belong to the current workflow.
    - User approval is required.
    - Application must not require further review.
    - Only ready-to-apply applications can proceed.
    - This function does NOT submit any application.
    """

    if not isinstance(application, dict):
        raise ValueError("Application data must be a dictionary")

    approved = application.get("approved", False)
    requires_user_review = application.get(
        "requires_user_review",
        True
    )
    status = application.get("status")

    if not approved:
        return {
            "allowed": False,
            "message": "Application has not been approved by the user.",
            "requires_user_confirmation": True,
            "status": status
        }

    if requires_user_review:
        return {
            "allowed": False,
            "message": "Application still requires user review.",
            "requires_user_confirmation": True,
            "status": status
        }

    if status != "ready-to-apply":
        return {
            "allowed": False,
            "message": "Application is not ready to apply.",
            "requires_user_confirmation": True,
            "status": status
        }

    return {
        "allowed": True,
        "message": (
            "Application passed the submission safety gate. "
            "Final human confirmation is still required."
        ),
        "requires_user_confirmation": True,
        "status": status,
        "submitted": False,
        "safety_note": (
            "This gate does not submit the application. "
            "Final human confirmation is required before any submission."
        )
    }