import os
from dataclasses import dataclass
from html import escape
from urllib.parse import urlencode

import sib_api_v3_sdk
from dotenv import load_dotenv
from sib_api_v3_sdk.rest import ApiException

load_dotenv()


class EmailDeliveryError(RuntimeError):
    """Raised when Brevo cannot accept an email for delivery."""


@dataclass(frozen=True)
class EmailSettings:
    api_key: str
    sender_email: str
    sender_name: str
    app_base_url: str

    @classmethod
    def from_environment(cls) -> "EmailSettings":
        values = {
            "api_key": os.getenv("BREVO_API_KEY"),
            "sender_email": os.getenv("BREVO_SENDER_EMAIL"),
            "sender_name": os.getenv("BREVO_SENDER_NAME", "Wymiana zajec"),
            "app_base_url": os.getenv("APP_BASE_URL", "http://localhost:8000"),
        }
        missing = [
            environment_name
            for environment_name, value in (
                ("BREVO_API_KEY", values["api_key"]),
                ("BREVO_SENDER_EMAIL", values["sender_email"]),
            )
            if not value
        ]
        if missing:
            raise EmailDeliveryError(
                "Missing email configuration: " + ", ".join(missing)
            )
        return cls(**values)  # type: ignore[arg-type]


def send_email(
    *,
    recipient_email: str,
    subject: str,
    html_content: str,
    text_content: str,
    settings: EmailSettings | None = None,
) -> None:
    settings = settings or EmailSettings.from_environment()
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = settings.api_key

    message = sib_api_v3_sdk.SendSmtpEmail(
        sender={"name": settings.sender_name, "email": settings.sender_email},
        to=[{"email": recipient_email}],
        subject=subject,
        html_content=html_content,
        text_content=text_content,
    )

    try:
        api_client = sib_api_v3_sdk.ApiClient(configuration)
        sib_api_v3_sdk.TransactionalEmailsApi(api_client).send_transac_email(message)
    except ApiException as error:
        raise EmailDeliveryError("Brevo rejected the email") from error


def send_verification_email(
    *,
    recipient_email: str,
    verification_token: str,
    valid_for_days: int = 7,
    settings: EmailSettings | None = None,
) -> None:
    settings = settings or EmailSettings.from_environment()
    verification_url = (
        f"{settings.app_base_url.rstrip('/')}/verify?"
        f"{urlencode({'token': verification_token})}"
    )
    safe_url = escape(verification_url, quote=True)
    send_email(
        recipient_email=recipient_email,
        subject="Potwierdz adres email w Wymianie zajec",
        html_content=(
            "<p>Potwierdz swoj adres email, aby aktywowac konto:</p>"
            f'<p><a href="{safe_url}">Potwierdz adres email</a></p>'
            f"<p>Link jest wazny przez {valid_for_days} dni.</p>"
        ),
        text_content=(
            "Potwierdz swoj adres email, aby aktywowac konto: "
            f"{verification_url}\nLink jest wazny przez {valid_for_days} dni."
        ),
        settings=settings,
    )

def send_exchange_request_email(
    *, recipient_email: str, listing_subject: str, settings: EmailSettings | None = None
) -> None:
    send_email(
        recipient_email=recipient_email,
        subject="Nowe zgloszenie wymiany",
        html_content=f"<p>Ktos zglosil sie do wymiany przedmiotu: <b>{escape(listing_subject)}</b>.</p>",
        text_content=f"Ktos zglosil sie do wymiany przedmiotu: {listing_subject}.",
        settings=settings,
    )

def send_exchange_confirmed_email(
    *, recipient_email: str, listing_subject: str, settings: EmailSettings | None = None
) -> None:
    send_email(
        recipient_email=recipient_email,
        subject="Wymiana zostala potwierdzona",
        html_content=f"<p>Wymiana przedmiotu <b>{escape(listing_subject)}</b> zostala potwierdzona.</p>",
        text_content=f"Wymiana przedmiotu {listing_subject} zostala potwierdzona.",
        settings=settings,
    )

def send_password_reset_email(
    *,
    recipient_email: str,
    reset_token: str,
    valid_for_hours: int = 1,
    settings: EmailSettings | None = None,
) -> None:
    settings = settings or EmailSettings.from_environment()
    reset_url = (
        f"{settings.app_base_url.rstrip('/')}/reset-password?"
        f"{urlencode({'token': reset_token})}"
    )
    safe_url = escape(reset_url, quote=True)
    send_email(
        recipient_email=recipient_email,
        subject="Reset hasla w Wymianie Grup PW",
        html_content=(
            "<p>Otrzymalismy prosbe o reset hasla.</p>"
            f'<p><a href="{safe_url}">Ustaw nowe haslo</a></p>'
            f"<p>Link jest wazny przez {valid_for_hours} godzine.</p>"
        ),
        text_content=(
            "Ustaw nowe haslo: "
            f"{reset_url}\nLink jest wazny przez {valid_for_hours} godzine."
        ),
        settings=settings,
    )