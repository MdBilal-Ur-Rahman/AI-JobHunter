
import pytest

from app.services import url_verification_service as url_service


@pytest.fixture
def mock_public_dns(monkeypatch):
    """Mock DNS to return a public IP for URL validation tests."""

    def fake_getaddrinfo(hostname, port, type=None):
        return [
            (
                2,
                1,
                6,
                "",
                ("8.8.8.8", port),
            )
        ]

    monkeypatch.setattr(
        url_service.socket,
        "getaddrinfo",
        fake_getaddrinfo,
    )


@pytest.mark.parametrize(
    ("url", "expected_domain"),
    [
        ("https://naukri.com/jobs", "naukri.com"),
        ("https://builtin.com/jobs", "builtin.com"),
        ("https://www.builtin.com/jobs", "builtin.com"),
        ("https://simplyhired.co.in/jobs", "simplyhired.co.in"),
        ("https://www.simplyhired.co.in/jobs", "simplyhired.co.in"),
        (
            "https://www.glassdoor.co.in/jobs",
            "glassdoor.co.in",
        ),
        (
            "https://glassdoor.co.in/jobs",
            "glassdoor.co.in",
        ),
        (
            "https://www.ambitionbox.com/jobs",
            "ambitionbox.com",
        ),
        (
            "https://ambitionbox.com/jobs",
            "ambitionbox.com",
        ),
        (
            "https://apna.co/job/chennai-region/bde-123",
            "apna.co",
        ),
    ],
)
def test_trusted_domains_with_public_dns_are_accepted(
    mock_public_dns,
    url,
    expected_domain,
):
    """Trusted domains with public DNS should pass URL validation."""

    result = url_service.validate_application_url(url)

    assert result["valid"] is True
    assert result["job_verified"] is False
    assert result["verification_blocked"] is False
    assert result["trusted_domain"] == expected_domain


@pytest.mark.parametrize(
    "url",
    [
        "https://evil-example.com/redirect",
        "https://naukri.com.evil-example.com/job",
        "https://naukri.com.attacker.example/job",
        "https://fake-builtin.com/jobs",
        "https://builtin.com.evil-example.com/jobs",
        "https://simplyhired.co.in.evil-example.com/jobs",
        "https://simplyhired.com.evil-example.com/jobs",
        "https://glassdoor.co.in.evil-example.com/jobs",
        "https://ambitionbox.com.evil-example.com/jobs",
    ],
)
def test_untrusted_and_lookalike_domains_are_rejected(url):
    """Untrusted and lookalike domains must be rejected."""

    result = url_service.validate_application_url(url)

    assert result["valid"] is False
    assert result["job_verified"] is False
    assert "trusted" in result["error"].lower()


def test_http_url_is_rejected():
    """HTTP URLs must be rejected."""

    result = url_service.validate_application_url(
        "http://naukri.com/job"
    )

    assert result["valid"] is False
    assert result["job_verified"] is False
    assert "HTTPS" in result["error"]


def test_private_ip_url_is_rejected():
    """Direct private IP URLs must be rejected."""

    result = url_service.validate_application_url(
        "https://127.0.0.1/internal"
    )

    assert result["valid"] is False
    assert result["job_verified"] is False


def test_dns_failure_is_rejected(monkeypatch):
    """DNS failures must fail closed."""

    def fail_dns(*args, **kwargs):
        raise OSError("Simulated DNS failure")

    monkeypatch.setattr(
        url_service.socket,
        "getaddrinfo",
        fail_dns,
    )

    result = url_service.validate_application_url(
        "https://naukri.com"
    )

    assert result["valid"] is False
    assert result["job_verified"] is False


def test_private_ip_returned_by_dns_is_rejected(monkeypatch):
    """A trusted hostname resolving to a private IP must be rejected."""

    def private_dns(hostname, port, type=None):
        return [
            (
                2,
                1,
                6,
                "",
                ("192.168.1.10", port),
            )
        ]

    monkeypatch.setattr(
        url_service.socket,
        "getaddrinfo",
        private_dns,
    )

    result = url_service.validate_application_url(
        "https://naukri.com"
    )

    assert result["valid"] is False
    assert result["job_verified"] is False


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "javascript:alert(1)",
        "https://username:password@naukri.com",
        "https://naukri.com:8443",
    ],
)
def test_unsafe_url_formats_are_rejected(url):
    """Malformed or unsupported URL formats must be rejected."""

    result = url_service.validate_application_url(url)

    assert result["valid"] is False
    assert result["job_verified"] is False


def test_verify_application_url_uses_same_validation(mock_public_dns):
    """The public verification entry point should use the same rules."""

    result = url_service.verify_application_url(
        "https://www.ambitionbox.com/jobs"
    )

    assert result["valid"] is True
    assert result["job_verified"] is False
    assert result["trusted_domain"] == "ambitionbox.com"


def test_trailing_dot_hostname_is_normalized(mock_public_dns):
    """A trailing DNS dot should not break trusted-domain matching."""

    result = url_service.validate_application_url(
        "https://naukri.com./jobs"
    )

    assert result["valid"] is True
    assert result["trusted_domain"] == "naukri.com"
