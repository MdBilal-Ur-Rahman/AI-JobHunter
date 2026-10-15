
import pytest

from app.services import url_verification_service as url_service


@pytest.fixture
def mock_public_dns(monkeypatch):
    """Test ke dauran DNS ko ek public IP return karwao."""

    def fake_getaddrinfo(hostname, port, type=None):
        return [
            (2, 1, 6, "", ("8.8.8.8", port))
        ]

    monkeypatch.setattr(
        url_service.socket,
        "getaddrinfo",
        fake_getaddrinfo,
    )


def test_untrusted_domain_is_rejected():
    result = url_service._validate_https_url(
        "https://evil-example.com/redirect"
    )

    assert result["valid"] is False
    assert result["job_verified"] is False

def test_fake_trusted_domain_is_rejected():
    result = url_service._validate_https_url(
        "https://naukri.com.evil-example.com/job"
    )

    assert result["valid"] is False
    assert result["job_verified"] is False


def test_http_destination_is_rejected():
    result = url_service._validate_https_url(
        "http://naukri.com/job"
    )

    assert result["valid"] is False
    assert result["job_verified"] is False


def test_private_ip_destination_is_rejected():
    result = url_service._validate_https_url(
        "https://127.0.0.1/internal"
    )

    assert result["valid"] is False
    assert result["job_verified"] is False


def test_trusted_domain_with_public_dns_is_accepted(
    mock_public_dns,
):
    result = url_service._validate_https_url(
        "https://naukri.com/jobs"
    )

    assert result["valid"] is True
    assert result["hostname"] == "naukri.com"
    assert result["trusted_domain"] == "naukri.com"


def test_dns_failure_is_rejected(monkeypatch):
    def fail_dns(*args, **kwargs):
        raise OSError("Simulated DNS failure")

    monkeypatch.setattr(
        url_service.socket,
        "getaddrinfo",
        fail_dns,
    )

    result = url_service._validate_https_url(
        "https://naukri.com"
    )

    assert result["valid"] is False
    assert "could not be resolved" in result["message"]


def test_private_ip_returned_by_dns_is_rejected(monkeypatch):
    def private_dns(hostname, port, type=None):
        return [
            (2, 1, 6, "", ("192.168.1.10", port))
        ]

    monkeypatch.setattr(
        url_service.socket,
        "getaddrinfo",
        private_dns,
    )

    result = url_service._validate_https_url(
        "https://naukri.com"
    )

    assert result["valid"] is False
    assert "non-public IP" in result["message"]


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
    result = url_service._validate_https_url(url)

    assert result["valid"] is False
    assert result["job_verified"] is False
