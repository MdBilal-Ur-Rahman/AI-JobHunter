import json
from pathlib import Path

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from app.services.application_field_mapping_service import (
    map_application_fields,
)
from app.services.application_form_filling_service import (
    fill_application_form,
)


DEMO_FORM_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "automation"
    / "demo_application.html"
)

SAMPLE_VERIFIED_RESUME = """
Avery Example
avery@example.com | Demo City, Telangana
5550101234
Software developer
"""


@pytest.fixture
def demo_page():
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except PlaywrightError as error:
            if "Executable doesn't exist" in str(error):
                pytest.skip(
                    "Install Chromium with `python -m playwright install chromium`."
                )
            raise

        try:
            page = browser.new_page()
            page.set_content(
                DEMO_FORM_PATH.read_text(encoding="utf-8")
            )
            page.evaluate(
                """() => {
                    window.submissionCount = 0;
                    document.querySelector("form").addEventListener(
                        "submit",
                        () => window.submissionCount += 1
                    );
                }"""
            )
            yield page
        finally:
            browser.close()


def get_page_fields(page):
    fields = []
    for control in page.locator(
        "input, textarea, select"
    ).all():
        name = control.get_attribute("name")
        if name:
            fields.append({
                "name": name,
                "id": control.get_attribute("id"),
                "tag": control.evaluate(
                    "(element) => element.tagName.toLowerCase()"
                ),
                "type": control.get_attribute("type"),
                "placeholder": control.get_attribute("placeholder"),
            })
    return fields


def test_verified_resume_fills_local_demo_without_submitting(demo_page):
    mapping = map_application_fields(
        verified_resume=SAMPLE_VERIFIED_RESUME,
        fields=get_page_fields(demo_page),
    )

    result = fill_application_form(
        page=demo_page,
        field_mappings=mapping,
    )

    assert {
        field["field_name"] for field in result["filled_fields"]
    } == {"full_name", "email", "phone", "location"}
    assert any(
        field["field_name"] == "cover_letter"
        for field in result["skipped_fields"]
    )
    assert demo_page.locator('[name="full_name"]').input_value() == (
        "Avery Example"
    )
    assert demo_page.locator('[name="email"]').input_value() == (
        "avery@example.com"
    )
    assert result["submitted"] is False
    assert result["requires_user_approval"] is True
    assert demo_page.evaluate(
        "() => window.submissionCount"
    ) == 0
    assert "avery@example.com" not in json.dumps(result)


def test_untrusted_mapping_cannot_use_selector_text_to_fill_submit(demo_page):
    result = fill_application_form(
        page=demo_page,
        field_mappings={
            "verified": True,
            "source": "verified_resume",
            "mappings": [{
                "field_name": 'email"], input[type="submit"]',
                "available": True,
                "value": "Avery Example",
                "source": "verified_resume",
            }],
        },
    )

    assert result["filled_fields"] == []
    assert len(result["skipped_fields"]) == 1
    assert demo_page.locator('[name="email"]').input_value() == ""
    assert result["submitted"] is False
    assert demo_page.evaluate(
        "() => window.submissionCount"
    ) == 0


def test_form_fill_rejects_unverified_mapping(demo_page):
    with pytest.raises(ValueError, match="verified-resume"):
        fill_application_form(
            page=demo_page,
            field_mappings={
                "verified": False,
                "source": "unverified",
                "mappings": [],
            },
        )
