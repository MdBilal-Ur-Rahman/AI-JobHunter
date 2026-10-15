import pytest

from app.services.application_submission_gate_service import (
    check_submission_gate,
)


@pytest.mark.parametrize(
    ("application", "expected_message"),
    [
        (
            {"approved": False, "status": "ready-to-apply"},
            "not been approved",
        ),
        (
            {
                "approved": True,
                "requires_user_review": True,
                "status": "ready-to-apply",
            },
            "requires user review",
        ),
        (
            {
                "approved": True,
                "requires_user_review": False,
                "status": "shortlisted",
            },
            "not ready to apply",
        ),
    ],
)
def test_submission_gate_fails_closed(application, expected_message):
    result = check_submission_gate(application)

    assert result["allowed"] is False
    assert expected_message in result["message"]
    assert result["requires_user_confirmation"] is True


def test_approved_application_still_is_not_submitted():
    result = check_submission_gate({
        "approved": True,
        "requires_user_review": False,
        "status": "ready-to-apply",
    })

    assert result["allowed"] is True
    assert result["submitted"] is False
    assert result["requires_user_confirmation"] is True


def test_submission_gate_rejects_invalid_application_data():
    with pytest.raises(ValueError, match="Application data"):
        check_submission_gate(None)
