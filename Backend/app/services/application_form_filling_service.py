from typing import Any, Dict

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page


def fill_application_form(
    page: Page,
    field_mappings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Fill application form using verified field mappings.

    Safety rules:
    - Only fill fields marked as available.
    - Never invent missing information.
    - Never submit the application.
    - Never click the submit button.
    - Never bypass CAPTCHA or OTP.
    """

    if page is None:
        raise ValueError(
            "Playwright page is required"
        )

    if not isinstance(field_mappings, dict):
        raise ValueError(
            "Field mappings must be a dictionary"
        )

    if (
        field_mappings.get("verified") is not True
        or field_mappings.get("source") != "verified_resume"
    ):
        raise ValueError(
            "Only verified-resume field mappings can be filled"
        )

    mappings = field_mappings.get("mappings", [])

    if not isinstance(mappings, list):
        raise ValueError(
            "Mappings must be a list"
        )

    filled_fields = []
    skipped_fields = []
    controls = page.locator(
        "input, textarea, select"
    ).all()

    for mapping in mappings:

        if not isinstance(mapping, dict):
            skipped_fields.append({
                "field_name": None,
                "reason": "Field mapping must be an object."
            })
            continue

        field_name = mapping.get(
            "field_name"
        )

        available = mapping.get(
            "available",
            False
        )

        value = mapping.get(
            "value"
        )

        if not isinstance(field_name, str) or not field_name.strip():
            skipped_fields.append({
                "field_name": None,
                "reason": "Field mapping is missing a valid field name."
            })
            continue

        if (
            available is not True
            or mapping.get("source") != "verified_resume"
            or not isinstance(value, str)
            or not value.strip()
        ):
            skipped_fields.append({
                "field_name": field_name,
                "reason": (
                    "Verified resume information is not available."
                )
            })
            continue

        try:
            matches = [
                control
                for control in controls
                if control.get_attribute("name") == field_name
            ]

            if len(matches) != 1:
                skipped_fields.append({
                    "field_name": field_name,
                    "reason": (
                        "A unique matching form field was not found."
                    )
                })
                continue

            locator = matches[0]
            tag = locator.evaluate(
                "(element) => element.tagName.toLowerCase()"
            )
            input_type = (
                locator.get_attribute("type") or "text"
            ).lower()

            if tag == "input" and input_type not in {
                "text",
                "email",
                "tel",
                "url",
                "search",
                "number",
                "date",
            }:
                skipped_fields.append({
                    "field_name": field_name,
                    "reason": "This input type is not safe to fill."
                })
                continue

            if tag == "select":
                locator.select_option(label=value)
            elif tag in {"input", "textarea"}:
                locator.fill(value)
            else:
                skipped_fields.append({
                    "field_name": field_name,
                    "reason": "This form control is not supported."
                })
                continue

            filled_fields.append({
                "field_name": field_name,
                "source": "verified_resume"
            })

        except PlaywrightError as error:
            skipped_fields.append({
                "field_name": field_name,
                "reason": (
                    "Playwright could not fill this field "
                    f"({type(error).__name__})."
                )
            })

    return {
        "message": (
            "Application form filled safely"
        ),
        "filled_fields": filled_fields,
        "skipped_fields": skipped_fields,
        "submitted": False,
        "requires_user_approval": True,
        "safety_note": (
            "Only verified resume information "
            "was entered. The application was "
            "not submitted."
        )
    }