import pytest

import email_service
from email_service import EmailDeliveryError, EmailSettings, send_verification_email


def test_verification_email_contains_encoded_link(monkeypatch):
    captured = {}

    def fake_send_email(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(email_service, "send_email", fake_send_email)
    settings = EmailSettings(
        api_key="test-key",
        sender_email="noreply@example.com",
        sender_name="Wymiana zajec",
        app_base_url="https://example.com/",
    )

    send_verification_email(
        recipient_email="12345678@pw.edu.pl",
        verification_token="token with spaces",
        settings=settings,
    )

    assert captured["recipient_email"] == "12345678@pw.edu.pl"
    assert "https://example.com/verify?token=token+with+spaces" in captured["text_content"]
    assert "wazny przez 7 dni" in captured["text_content"]
    assert "token+with+spaces" in captured["html_content"]


def test_missing_brevo_configuration_is_reported(monkeypatch):
    monkeypatch.delenv("BREVO_API_KEY", raising=False)
    monkeypatch.delenv("BREVO_SENDER_EMAIL", raising=False)

    with pytest.raises(
        EmailDeliveryError,
        match="BREVO_API_KEY, BREVO_SENDER_EMAIL",
    ):
        EmailSettings.from_environment()