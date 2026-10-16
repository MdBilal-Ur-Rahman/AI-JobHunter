import hashlib
import os
import secrets
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from urllib.parse import urlencode, urlsplit, urlunsplit


class PasswordResetDeliveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class PasswordResetMailSettings:
    host: str
    port: int
    username: str | None
    password: str | None
    from_email: str
    frontend_base_url: str


def get_password_reset_mail_settings() -> PasswordResetMailSettings:
    host = os.getenv("SMTP_HOST", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", "").strip()
    frontend_base_url = os.getenv("FRONTEND_BASE_URL", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip() or None
    password = os.getenv("SMTP_PASSWORD") or None

    if not host or not from_email or not frontend_base_url:
        raise PasswordResetDeliveryError(
            "Password reset email is not configured."
        )

    if bool(username) != bool(password):
        raise PasswordResetDeliveryError(
            "SMTP username and password must be configured together."
        )

    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError as exc:
        raise PasswordResetDeliveryError(
            "SMTP_PORT must be a valid port number."
        ) from exc

    if not 1 <= port <= 65535:
        raise PasswordResetDeliveryError(
            "SMTP_PORT must be between 1 and 65535."
        )

    parsed_url = urlsplit(frontend_base_url)
    if (
        parsed_url.scheme not in {"http", "https"}
        or not parsed_url.netloc
        or parsed_url.username
        or parsed_url.password
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise PasswordResetDeliveryError(
            "FRONTEND_BASE_URL must be an HTTP(S) origin or base path."
        )

    return PasswordResetMailSettings(
        host=host,
        port=port,
        username=username,
        password=password,
        from_email=from_email,
        frontend_base_url=frontend_base_url.rstrip("/"),
    )


def hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hash_password_reset_token(token)


def build_password_reset_url(
    token: str,
    frontend_base_url: str,
) -> str:
    parsed_url = urlsplit(frontend_base_url)
    path = f"{parsed_url.path.rstrip('/')}/reset-password"
    return urlunsplit(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            path,
            urlencode({"token": token}),
            "",
        )
    )


def send_password_reset_email(
    recipient: str,
    reset_url: str,
    settings: PasswordResetMailSettings,
) -> None:
    try:
        message = EmailMessage()
        message["Subject"] = "Reset your AI JobHunter password"
        message["From"] = settings.from_email
        message["To"] = recipient
        message.set_content(
            "We received a request to reset your AI JobHunter password.\n\n"
            f"Set a new password using this one-time link (valid for 30 minutes):\n"
            f"{reset_url}\n\n"
            "If you did not request this, you can ignore this email."
        )

        with smtplib.SMTP(
            settings.host,
            settings.port,
            timeout=10,
        ) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()

            if settings.username and settings.password:
                smtp.login(settings.username, settings.password)

            smtp.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        raise PasswordResetDeliveryError(
            "Could not deliver the password reset email."
        ) from exc
