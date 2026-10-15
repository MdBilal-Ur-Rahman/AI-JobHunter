from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from app.services.url_verification_service import (
    validate_application_url,
)


_playwright = None
_browser = None

MAX_REDIRECTS = 5


def _validate_url(url: str) -> dict:
    """
    Validate a URL before allowing the browser to request it.

    The URL verification service checks HTTPS, trusted domains,
    DNS resolution, and public IP addresses.
    """
    try:
        result = validate_application_url(url)

        if not isinstance(result, dict):
            return {
                "valid": False,
                "message": "Unexpected URL validation response.",
            }

        return result

    except Exception:
        return {
            "valid": False,
            "message": "URL validation failed.",
        }


def _get_redirect_count(request) -> int:
    """
    Count the redirect chain leading to this request.
    """
    count = 0
    previous_request = request.redirected_from

    while previous_request is not None:
        count += 1
        previous_request = previous_request.redirected_from

    return count


def _install_request_guard(page):
    """
    Validate every browser request before allowing it.

    This is a defense-in-depth measure, not a complete SSRF
    defense. Browser-level network isolation is still recommended.
    """

    def handle_route(route):
        request = route.request
        request_url = request.url

        try:
            parsed = urlparse(request_url)

            # Only HTTPS network requests are allowed.
            if parsed.scheme.lower() != "https":
                route.abort()
                return

            # Reject redirects exceeding the configured limit.
            if _get_redirect_count(request) > MAX_REDIRECTS:
                route.abort()
                return

            # Validate the destination before allowing the request.
            validation = _validate_url(request_url)

            if not validation.get("valid", False):
                route.abort()
                return

            route.continue_()

        except Exception:
            # Fail closed if the security check fails.
            try:
                route.abort()
            except Exception:
                pass

    page.route("**/*", handle_route)


def _get_browser():
    """
    Start Playwright and Chromium when needed.
    """
    global _playwright
    global _browser

    if _playwright is None:
        _playwright = sync_playwright().start()

    if _browser is None:
        _browser = _playwright.chromium.launch(
            headless=True
        )

    return _browser


def _create_safe_page():
    """
    Create a browser page with request interception enabled.
    """
    browser = _get_browser()

    page = browser.new_page(
        accept_downloads=False
    )

    _install_request_guard(page)

    return page


def open_application_page(application_url: str):
    """
    Open a validated application page.

    Redirects and browser requests are checked before being allowed.
    The browser does not submit application forms.
    """

    if not isinstance(application_url, str) or not application_url.strip():
        return {
            "message": "Application URL is required.",
            "requested_url": application_url,
            "final_url": None,
            "redirected": False,
            "blocked": True,
        }

    application_url = application_url.strip()

    initial_validation = _validate_url(application_url)

    if not initial_validation.get("valid", False):
        return {
            "message": "Application URL failed security validation.",
            "requested_url": application_url,
            "final_url": None,
            "redirected": False,
            "blocked": True,
            "reason": initial_validation.get(
                "message",
                "URL validation failed.",
            ),
        }

    page = None

    try:
        page = _create_safe_page()

        page.goto(
            application_url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        final_url = page.url

        # Check the final destination again.
        final_validation = _validate_url(final_url)

        if not final_validation.get("valid", False):
            page.close()

            return {
                "message": "Final destination failed security validation.",
                "requested_url": application_url,
                "final_url": final_url,
                "redirected": True,
                "blocked": True,
            }

        redirected = (
            final_url.rstrip("/")
            != application_url.rstrip("/")
        )

        return {
            "message": (
                "Application page opened successfully."
                if not redirected
                else "Application page opened after a validated redirect."
            ),
            "requested_url": application_url,
            "final_url": final_url,
            "url": final_url,
            "title": page.title(),
            "redirected": redirected,
            "blocked": False,
        }

    except Exception:
        if page is not None:
            try:
                page.close()
            except Exception:
                pass

        return {
            "message": (
                "Navigation failed or was blocked by security controls."
            ),
            "requested_url": application_url,
            "final_url": None,
            "redirected": False,
            "blocked": True,
        }


def inspect_application_page(application_url: str):
    """
    Safely inspect an application page.

    Safety rules:
    - Validate the initial URL.
    - Validate browser requests and redirect destinations.
    - Do not submit forms.
    - Do not click buttons.
    - Do not log in.
    - Do not bypass CAPTCHA or OTP.
    - Only inspect page metadata and form fields.
    """

    if not isinstance(application_url, str) or not application_url.strip():
        raise ValueError("Application URL is required.")

    application_url = application_url.strip()

    initial_validation = _validate_url(application_url)

    if not initial_validation.get("valid", False):
        return {
            "message": "Application URL failed security validation.",
            "requested_url": application_url,
            "final_url": None,
            "title": None,
            "redirected": False,
            "blocked": True,
            "form_count": 0,
            "forms": [],
        }

    page = None

    try:
        page = _create_safe_page()

        page.goto(
            application_url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        final_url = page.url

        final_validation = _validate_url(final_url)

        if not final_validation.get("valid", False):
            return {
                "message": "Final destination failed security validation.",
                "requested_url": application_url,
                "final_url": final_url,
                "title": None,
                "redirected": True,
                "blocked": True,
                "form_count": 0,
                "forms": [],
            }

        forms = []

        for form in page.locator("form").all():
            inputs = []

            for element in form.locator(
                "input, textarea, select"
            ).all():

                try:
                    inputs.append({
                        "tag": element.evaluate(
                            "(el) => el.tagName.toLowerCase()"
                        ),
                        "type": element.get_attribute("type"),
                        "name": element.get_attribute("name"),
                        "id": element.get_attribute("id"),
                        "placeholder": element.get_attribute(
                            "placeholder"
                        ),
                    })

                except Exception:
                    continue

            forms.append({
                "input_count": len(inputs),
                "inputs": inputs,
            })

        return {
            "message": "Application page inspected safely.",
            "requested_url": application_url,
            "final_url": final_url,
            "title": page.title(),
            "redirected": (
                final_url.rstrip("/")
                != application_url.rstrip("/")
            ),
            "blocked": False,
            "form_count": len(forms),
            "forms": forms,
            "safety_note": (
                "The page was inspected without submitting "
                "any application form."
            ),
        }

    except Exception:
        return {
            "message": (
                "Page inspection failed or navigation was blocked."
            ),
            "requested_url": application_url,
            "final_url": None,
            "title": None,
            "redirected": False,
            "blocked": True,
            "form_count": 0,
            "forms": [],
        }

    finally:
        if page is not None:
            try:
                page.close()
            except Exception:
                pass


def open_application_page_for_user(
    application_url: str,
):
    return open_application_page(application_url)