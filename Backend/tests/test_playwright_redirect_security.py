
from unittest.mock import Mock

from app.services.playwright_service import (
    _get_redirect_count,
    _install_request_guard,
)


def test_redirect_count_without_redirects():
    request = Mock()
    request.redirected_from = None

    assert _get_redirect_count(request) == 0


def test_redirect_count_with_one_redirect():
    original_request = Mock()
    original_request.redirected_from = None

    redirected_request = Mock()
    redirected_request.redirected_from = original_request

    assert _get_redirect_count(redirected_request) == 1


def test_redirect_count_with_multiple_redirects():
    first_request = Mock()
    first_request.redirected_from = None

    second_request = Mock()
    second_request.redirected_from = first_request

    third_request = Mock()
    third_request.redirected_from = second_request

    assert _get_redirect_count(third_request) == 2


def test_request_guard_blocks_http_requests(monkeypatch):
    page = Mock()
    route_handler = {}

    def capture_route(pattern, handler):
        route_handler["handler"] = handler

    page.route.side_effect = capture_route

    _install_request_guard(page)

    route = Mock()
    route.request.url = "http://example.com"
    route.request.redirected_from = None

    route_handler["handler"](route)

    route.abort.assert_called_once()
    route.continue_.assert_not_called()


def test_request_guard_blocks_untrusted_domains(monkeypatch):
    page = Mock()
    route_handler = {}

    def capture_route(pattern, handler):
        route_handler["handler"] = handler

    page.route.side_effect = capture_route

    monkeypatch.setattr(
        "app.services.playwright_service._validate_url",
        lambda url: {
            "valid": False,
            "message": "Untrusted domain",
        },
    )

    _install_request_guard(page)

    route = Mock()
    route.request.url = "https://example.com/job"
    route.request.redirected_from = None

    route_handler["handler"](route)

    route.abort.assert_called_once()
    route.continue_.assert_not_called()


def test_request_guard_allows_valid_https_url(monkeypatch):
    page = Mock()
    route_handler = {}

    def capture_route(pattern, handler):
        route_handler["handler"] = handler

    page.route.side_effect = capture_route

    monkeypatch.setattr(
        "app.services.playwright_service._validate_url",
        lambda url: {
            "valid": True,
            "message": None,
        },
    )

    _install_request_guard(page)

    route = Mock()
    route.request.url = "https://indeed.com/jobs"
    route.request.redirected_from = None

    route_handler["handler"](route)

    route.continue_.assert_called_once()
    route.abort.assert_not_called()


def test_request_guard_blocks_excessive_redirects(monkeypatch):
    page = Mock()
    route_handler = {}

    def capture_route(pattern, handler):
        route_handler["handler"] = handler

    page.route.side_effect = capture_route

    monkeypatch.setattr(
        "app.services.playwright_service._validate_url",
        lambda url: {
            "valid": True,
            "message": None,
        },
    )

    _install_request_guard(page)

    request = Mock()
    request.url = "https://indeed.com/jobs"

    previous_request = None

    for _ in range(6):
        next_request = Mock()
        next_request.redirected_from = previous_request
        previous_request = next_request

    request.redirected_from = previous_request

    route = Mock()
    route.request = request

    route_handler["handler"](route)

    route.abort.assert_called_once()
    route.continue_.assert_not_called()
