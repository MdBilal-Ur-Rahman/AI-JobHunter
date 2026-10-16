
import ipaddress
import socket
from urllib.parse import urlparse


TRUSTED_JOB_DOMAINS = {
    # Job search platforms
    "indeed.com",
    "naukri.com",
    "wellfound.com",
    "instahyre.com",
    "cutshort.io",
    "shine.com",
    "foundit.in",
    "timesjobs.com",
    "hirist.com",
    "internshala.com",
    "freshersworld.com",
    "iimjobs.com",
    "glassdoor.com",
    "glassdoor.co.in",
    "linkedin.com",
    "apna.co",
    "remoteok.com",
    "weworkremotely.com",
    "flexjobs.com",
    "builtin.com",
    "simplyhired.co.in",
    "ambitionbox.com",

    # Recruitment platforms
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "smartrecruiters.com",
    "workdayjobs.com",
}


def _error_result(
    url,
    message,
    hostname=None,
    trusted_domain=None,
):
    """Return a consistent, fail-closed URL validation result."""
    return {
        "valid": False,
        "job_verified": False,
        "verification_blocked": True,
        "requested_url": url,
        "final_url": None,
        "hostname": hostname,
        "trusted_domain": trusted_domain,
        "message": message,
        "error": message,
    }


def _get_trusted_domain(hostname):
    """Return the trusted root domain matching a hostname."""
    if not hostname:
        return None

    hostname = hostname.lower().rstrip(".")

    for domain in TRUSTED_JOB_DOMAINS:
        if hostname == domain or hostname.endswith("." + domain):
            return domain

    return None


def _validate_https_url(url):
    """
    Perform preliminary URL validation.

    This function does not follow redirects or verify that a genuine
    job posting exists. Network-level protections are still required
    to defend browser navigation against SSRF and DNS rebinding.
    """
    if not isinstance(url, str) or not url.strip():
        return _error_result(url, "URL is empty or invalid.")

    url = url.strip()

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port
    except (ValueError, TypeError):
        return _error_result(url, "URL format is invalid.")

    if parsed.scheme.lower() != "https":
        return _error_result(
            url,
            "Only HTTPS URLs are allowed.",
            hostname=hostname,
        )

    if not hostname:
        return _error_result(url, "URL hostname is missing.")

    if parsed.username is not None or parsed.password is not None:
        return _error_result(
            url,
            "URLs containing usernames or passwords are not allowed.",
            hostname=hostname,
        )

    if port is not None and port != 443:
        return _error_result(
            url,
            "Only the standard HTTPS port 443 is allowed.",
            hostname=hostname,
        )

    hostname = hostname.lower().rstrip(".")

    if (
        hostname == "localhost"
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
    ):
        return _error_result(
            url,
            "Local hostnames are not allowed.",
            hostname=hostname,
        )

    # Direct IP-address URLs are not accepted.
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        return _error_result(
            url,
            "Direct IP-address URLs are not allowed.",
            hostname=hostname,
        )

    # Check the exact domain or a legitimate subdomain.
    trusted_domain = _get_trusted_domain(hostname)

    if trusted_domain is None:
        return _error_result(
            url,
            "The hostname is not in the trusted job-site domain list.",
            hostname=hostname,
        )

    # Resolve the hostname and reject all non-public IP addresses.
    try:
        addresses = socket.getaddrinfo(
            hostname,
            443,
            type=socket.SOCK_STREAM,
        )
    except OSError:
        return _error_result(
            url,
            "The hostname could not be resolved.",
            hostname=hostname,
            trusted_domain=trusted_domain,
        )

    if not addresses:
        return _error_result(
            url,
            "The hostname could not be resolved.",
            hostname=hostname,
            trusted_domain=trusted_domain,
        )

    for address in addresses:
        try:
            ip = ipaddress.ip_address(address[4][0])
        except (ValueError, IndexError, TypeError):
            return _error_result(
                url,
                "DNS returned an invalid IP address.",
                hostname=hostname,
                trusted_domain=trusted_domain,
            )

        if not ip.is_global:
            return _error_result(
                url,
                "DNS resolved to a non-public IP address.",
                hostname=hostname,
                trusted_domain=trusted_domain,
            )

    return {
        "valid": True,
        "job_verified": False,
        "verification_blocked": False,
        "requested_url": url,
        "final_url": url,
        "hostname": hostname,
        "trusted_domain": trusted_domain,
        "message": None,
        "error": None,
    }


def validate_application_url(url):
    """Validate an application URL synchronously."""
    return _validate_https_url(url)


def verify_application_url(url):
    """
    Synchronous URL verification entry point used by the application.

    This performs preliminary URL validation only. It does not follow
    redirects or establish that a genuine job posting exists.
    """
    return _validate_https_url(url)
