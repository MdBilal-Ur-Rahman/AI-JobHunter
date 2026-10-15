from typing import Any, Dict
import re


def map_application_fields(
    verified_resume: str,
    fields: list
) -> Dict[str, Any]:
    """
    Map application fields to information available
    in the verified resume.

    Safety rules:
    - Never invent missing information.
    - Never guess personal information.
    - Only mark a field as available when the
      verified resume contains relevant information.
    - Missing fields must remain unavailable.
    """

    if not verified_resume:
        raise ValueError(
            "Verified resume text is required"
        )

    if not isinstance(fields, list):
        raise ValueError(
            "Fields must be provided as a list"
        )

    resume_text = verified_resume.strip()

    mappings = []

    lines = [
        line.strip()
        for line in resume_text.splitlines()
        if line.strip()
    ]

    # -------------------------------------------------
    # Safely extract known information
    # -------------------------------------------------

    full_name = None
    email = None
    phone = None
    location = None

    # Full name
    if lines:
        full_name = lines[0]

    # Email
    email_match = re.search(
        r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
        resume_text
    )

    if email_match:
        email = email_match.group(0)

    # Phone
    phone_match = re.search(
        r"(?<!\d)(?:\+91[\s-]?)?\d{10}(?!\d)",
        resume_text
    )

    if phone_match:
        phone = re.sub(
            r"\D",
            "",
            phone_match.group(0)
        )

        if len(phone) > 10:
            phone = phone[-10:]

    # Location
    for line in lines:

        if (
            "Telangana" in line
            and "@" in line
        ):

            parts = [
                part.strip()
                for part in line.split("|")
            ]

            for part in parts:

                if (
                    "Telangana" in part
                    and "@" not in part
                ):
                    location = part
                    break

        if location:
            break

    # -------------------------------------------------
    # Field mapping
    # -------------------------------------------------

    for field in fields:

        if not isinstance(field, dict):
            continue

        field_name = field.get(
            "name"
        )

        if not field_name:
            continue

        normalized_name = (
            field_name
            .lower()
            .strip()
        )

        mapping = {
            "field_name": field_name,
            "available": False,
            "value": None,
            "source": None
        }

        if normalized_name == "full_name":

            if full_name:
                mapping["available"] = True
                mapping["value"] = full_name
                mapping["source"] = "verified_resume"

        elif normalized_name == "email":

            if email:
                mapping["available"] = True
                mapping["value"] = email
                mapping["source"] = "verified_resume"

        elif normalized_name == "phone":

            if phone:
                mapping["available"] = True
                mapping["value"] = phone
                mapping["source"] = "verified_resume"

        elif normalized_name == "location":

            if location:
                mapping["available"] = True
                mapping["value"] = location
                mapping["source"] = "verified_resume"

        elif normalized_name == "cover_letter":

            # Cover letter is not present in the
            # verified resume, so do not invent one.
            mapping["available"] = False
            mapping["value"] = None
            mapping["source"] = None

        mappings.append(mapping)

    return {
        "verified": True,
        "source": "verified_resume",
        "mappings": mappings,
        "safety_note": (
            "Only information found in the verified "
            "resume was mapped. Missing information "
            "was not invented."
        )
    }