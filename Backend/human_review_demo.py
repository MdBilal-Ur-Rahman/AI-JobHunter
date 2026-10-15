import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.services.application_field_mapping_service import (
    map_application_fields,
)
from app.services.application_form_filling_service import (
    fill_application_form,
)


DEMO_FORM_PATH = (
    Path(__file__).parent
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


def main() -> None:
    html = DEMO_FORM_PATH.read_text(encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        try:
            page = browser.new_page()
            page.set_content(html)
            page.evaluate(
                """() => {
                    window.submissionCount = 0;
                    document.querySelector("form").addEventListener(
                        "submit",
                        () => window.submissionCount += 1
                    );
                }"""
            )

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
                        "placeholder": control.get_attribute(
                            "placeholder"
                        ),
                    })

            mapping = map_application_fields(
                verified_resume=SAMPLE_VERIFIED_RESUME,
                fields=fields,
            )
            fill_result = fill_application_form(
                page=page,
                field_mappings=mapping,
            )
            submitted = page.evaluate(
                "() => window.submissionCount > 0"
            )

            if submitted or fill_result["submitted"]:
                raise RuntimeError(
                    "The demo must never submit the application."
                )

            print(json.dumps({
                "fields_found": len(fields),
                "filled_fields": fill_result["filled_fields"],
                "skipped_fields": fill_result["skipped_fields"],
                "submitted": submitted,
                "safety_note": fill_result["safety_note"],
            }, indent=2))
        finally:
            browser.close()


if __name__ == "__main__":
    main()
