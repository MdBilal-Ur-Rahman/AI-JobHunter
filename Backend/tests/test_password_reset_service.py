import pytest

from app.services import password_reset_service


def set_mail_environment(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "mailer@example.test")
    monkeypatch.setenv("SMTP_PASSWORD", "test-password")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "AI JobHunter <noreply@example.test>")
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://jobs.example.test/app")


def test_reset_tokens_are_random_and_stored_as_hashes():
    first_token, first_hash = password_reset_service.create_password_reset_token()
    second_token, second_hash = password_reset_service.create_password_reset_token()

    assert first_token != second_token
    assert first_hash != first_token
    assert second_hash != second_token
    assert password_reset_service.hash_password_reset_token(first_token) == first_hash


def test_reset_url_keeps_frontend_base_path_and_encodes_token():
    url = password_reset_service.build_password_reset_url(
        "token+with/slash",
        "https://jobs.example.test/app",
    )

    assert url == (
        "https://jobs.example.test/app/reset-password"
        "?token=token%2Bwith%2Fslash"
    )


def test_mail_configuration_requires_complete_smtp_credentials(monkeypatch):
    set_mail_environment(monkeypatch)
    monkeypatch.delenv("SMTP_PASSWORD")

    with pytest.raises(
        password_reset_service.PasswordResetDeliveryError,
        match="configured together",
    ):
        password_reset_service.get_password_reset_mail_settings()


def test_password_reset_email_uses_starttls_and_configured_sender(
    monkeypatch,
):
    set_mail_environment(monkeypatch)
    settings = password_reset_service.get_password_reset_mail_settings()
    captured = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("smtp.example.test", 587, 10)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def ehlo(self):
            captured["ehlo"] = True

        def starttls(self, context):
            captured["tls_context"] = context

        def login(self, username, password):
            captured["credentials"] = (username, password)

        def send_message(self, message):
            captured["message"] = message

    monkeypatch.setattr(password_reset_service.smtplib, "SMTP", FakeSMTP)

    password_reset_service.send_password_reset_email(
        "person@example.test",
        "https://jobs.example.test/reset-password?token=abc",
        settings,
    )

    assert captured["ehlo"] is True
    assert captured["tls_context"] is not None
    assert captured["credentials"] == (
        "mailer@example.test",
        "test-password",
    )
    assert captured["message"]["To"] == "person@example.test"
    assert (
        captured["message"]["From"]
        == "AI JobHunter <noreply@example.test>"
    )
    assert "one-time link" in captured["message"].get_content()
