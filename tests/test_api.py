from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from database import get_session
import main
from main import app
from main import token_hash
from models import (
    EmailDelivery,
    EmailDeliveryAttempt,
    EmailDeliveryStatus,
    ExchangeRequest,
    User,
)


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    main.limiter.reset()
    monkeypatch.setattr(main, "send_verification_email", lambda **kwargs: None)
    monkeypatch.setattr(main, "send_exchange_request_email", lambda **kwargs: None)
    monkeypatch.setattr(main, "send_exchange_confirmed_email", lambda **kwargs: None)
    monkeypatch.setattr(main, "send_password_reset_email", lambda **kwargs: None)
    with TestClient(app) as test_client:
        yield test_client, engine
    app.dependency_overrides.clear()


def register_and_verify(client: TestClient, engine, email: str, index_number: str):
    response = client.post(
        "/register",
        json={
            "email": email,
            "index_number": index_number,
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).one()
        user.email_verified = True
        session.add(user)
        session.commit()


def login(client: TestClient, email: str):
    response = client.post(
        "/login",
        json={"email": email, "password": "correct horse battery staple"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def listing_payload():
    return {
        "major": "mat",
        "semester": 3,
        "subject": "Algebra",
        "class_type": "tutorial",
        "group_have": "1",
        "group_want": "2",
        "description": "Zamiana grupy",
    }


def test_health_check(client):
    test_client, _ = client
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_configured_development_origin(client):
    test_client, _ = client
    response = test_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_unknown_host_is_rejected(client):
    test_client, _ = client
    response = test_client.get(
        "/health",
        headers={"Host": "not-allowed.example"},
    )
    assert response.status_code == 400


def test_public_listing_requires_authenticated_owner(client):
    test_client, engine = client
    register_and_verify(test_client, engine, "12345678@pw.edu.pl", "123456")
    owner_headers = login(test_client, "12345678@pw.edu.pl")

    response = test_client.post("/listings", json=listing_payload(), headers=owner_headers)
    assert response.status_code == 200
    listing_id = response.json()["id"]

    assert test_client.get(f"/listings/{listing_id}").status_code == 200
    assert (
        test_client.delete(f"/listings/{listing_id}", headers=owner_headers).status_code
        == 204
    )


def test_request_hides_listing_until_owner_confirms(client):
    test_client, engine = client
    register_and_verify(test_client, engine, "12345678@pw.edu.pl", "123456")
    register_and_verify(test_client, engine, "87654321@pw.edu.pl", "654321")
    owner_headers = login(test_client, "12345678@pw.edu.pl")
    requester_headers = login(test_client, "87654321@pw.edu.pl")

    listing = test_client.post(
        "/listings", json=listing_payload(), headers=owner_headers
    ).json()
    listing_id = listing["id"]

    request = test_client.post(
        f"/listings/{listing_id}/requests", headers=requester_headers
    )
    assert request.status_code == 201
    request_id = request.json()["id"]
    assert test_client.get("/listings").json() == []

    confirm = test_client.post(
        f"/exchange-requests/{request_id}/confirm", headers=owner_headers
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"
    assert test_client.get(f"/listings/{listing_id}").status_code == 404


def test_expired_request_reactivates_listing_and_blocks_owner(client):
    test_client, engine = client
    register_and_verify(test_client, engine, "12345678@pw.edu.pl", "123456")
    register_and_verify(test_client, engine, "87654321@pw.edu.pl", "654321")
    owner_headers = login(test_client, "12345678@pw.edu.pl")
    requester_headers = login(test_client, "87654321@pw.edu.pl")
    listing = test_client.post(
        "/listings", json=listing_payload(), headers=owner_headers
    ).json()

    request = test_client.post(
        f"/listings/{listing['id']}/requests", headers=requester_headers
    ).json()
    with Session(engine) as session:
        exchange_request = session.get(ExchangeRequest, request["id"])
        exchange_request.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.add(exchange_request)
        session.commit()

    assert test_client.get("/listings").status_code == 200
    blocked = test_client.post(
        "/listings", json=listing_payload(), headers=owner_headers
    )
    assert blocked.status_code == 403


def test_partial_update_cannot_make_groups_equal(client):
    test_client, engine = client
    register_and_verify(test_client, engine, "12345678@pw.edu.pl", "123456")
    owner_headers = login(test_client, "12345678@pw.edu.pl")
    listing = test_client.post(
        "/listings", json=listing_payload(), headers=owner_headers
    ).json()

    response = test_client.patch(
        f"/listings/{listing['id']}",
        json={"group_have": "2"},
        headers=owner_headers,
    )
    assert response.status_code == 422


def test_verification_expires_after_seven_days_and_resend_is_blocked_beforehand(client):
    test_client, engine = client
    response = test_client.post(
        "/register",
        json={
            "email": "12345678@pw.edu.pl",
            "index_number": "123456",
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == "12345678@pw.edu.pl")).one()
        assert user.verification_token_expires_at is not None
        user.verification_token_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.add(user)
        session.commit()

    resend = test_client.post(
        "/resend-verification", json={"email": "12345678@pw.edu.pl"}
    )
    assert resend.status_code == 200
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == "12345678@pw.edu.pl")).one()
        user.verification_token_expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        session.add(user)
        session.commit()
    assert (
        test_client.post(
            "/resend-verification", json={"email": "12345678@pw.edu.pl"}
        ).status_code
        == 429
    )


def test_verification_token_is_hashed_but_raw_token_still_works(client, monkeypatch):
    test_client, engine = client
    captured = {}

    def capture_verification_email(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(main, "send_verification_email", capture_verification_email)
    response = test_client.post(
        "/register",
        json={
            "email": "12345678@pw.edu.pl",
            "index_number": "123456",
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    raw_token = captured["verification_token"]
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == "12345678@pw.edu.pl")).one()
        assert user.verification_token_hash == token_hash(raw_token)
        assert raw_token not in user.verification_token_hash

    verification = test_client.get("/verify", params={"token": raw_token})
    assert verification.status_code == 200
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == "12345678@pw.edu.pl")).one()
        assert user.email_verified is True
        assert user.verification_token_hash is None


def test_email_delivery_records_success_and_attempt(client):
    test_client, engine = client
    register_and_verify(test_client, engine, "12345678@pw.edu.pl", "123456")
    with Session(engine) as session:
        delivery = session.exec(select(EmailDelivery)).one()
        attempt = session.exec(select(EmailDeliveryAttempt)).one()
        assert delivery.status == EmailDeliveryStatus.sent
        assert delivery.attempts == 1
        assert attempt.status == EmailDeliveryStatus.sent


def test_failed_email_is_recorded_and_registration_returns_503(client, monkeypatch):
    test_client, engine = client

    def fail_email(**kwargs):
        raise main.EmailDeliveryError("Brevo unavailable")

    monkeypatch.setattr(main, "send_verification_email", fail_email)
    response = test_client.post(
        "/register",
        json={
            "email": "12345678@pw.edu.pl",
            "index_number": "123456",
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 503
    with Session(engine) as session:
        delivery = session.exec(select(EmailDelivery)).one()
        attempt = session.exec(select(EmailDeliveryAttempt)).one()
        assert delivery.status == EmailDeliveryStatus.failed
        assert attempt.status == EmailDeliveryStatus.failed

    monkeypatch.setattr(main, "send_verification_email", lambda **kwargs: None)
    assert (
        test_client.post(
            "/resend-verification", json={"email": "12345678@pw.edu.pl"}
        ).status_code
        == 200
    )


def test_request_for_pending_listing_is_rejected(client):
    test_client, engine = client
    register_and_verify(test_client, engine, "12345678@pw.edu.pl", "123456")
    register_and_verify(test_client, engine, "87654321@pw.edu.pl", "654321")
    register_and_verify(test_client, engine, "11111111@pw.edu.pl", "111111")
    owner_headers = login(test_client, "12345678@pw.edu.pl")
    requester_headers = login(test_client, "87654321@pw.edu.pl")
    second_requester_headers = login(test_client, "11111111@pw.edu.pl")
    listing = test_client.post(
        "/listings", json=listing_payload(), headers=owner_headers
    ).json()
    listing_id = listing["id"]
    assert (
        test_client.post(
            f"/listings/{listing_id}/requests", headers=requester_headers
        ).status_code
        == 201
    )
    assert (
        test_client.post(
            f"/listings/{listing_id}/requests", headers=second_requester_headers
        ).status_code
        == 404
    )


def test_password_reset_is_one_time_and_revokes_existing_bearer(client, monkeypatch):
    test_client, engine = client
    register_and_verify(test_client, engine, "12345678@pw.edu.pl", "123456")
    old_headers = login(test_client, "12345678@pw.edu.pl")
    captured = {}

    def capture_reset_email(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(main, "send_password_reset_email", capture_reset_email)
    unknown = test_client.post(
        "/password-reset/request", json={"email": "99999999@pw.edu.pl"}
    )
    known = test_client.post(
        "/password-reset/request", json={"email": "12345678@pw.edu.pl"}
    )
    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json()

    reset = test_client.post(
        "/password-reset/confirm",
        json={"token": captured["reset_token"], "password": "new password 123"},
    )
    assert reset.status_code == 204
    assert (
        test_client.post(
            "/listings", json=listing_payload(), headers=old_headers
        ).status_code
        == 401
    )
    assert (
        test_client.post(
            "/password-reset/confirm",
            json={"token": captured["reset_token"], "password": "another password"},
        ).status_code
        == 400
    )
    assert (
        test_client.post(
            "/login",
            json={
                "email": "12345678@pw.edu.pl",
                "password": "new password 123",
            },
        ).status_code
        == 200
    )


def test_password_reset_request_is_rate_limited(client):
    test_client, _ = client
    statuses = [
        test_client.post(
            "/password-reset/request", json={"email": "99999999@pw.edu.pl"}
        ).status_code
        for _ in range(4)
    ]
    assert statuses == [202, 202, 202, 429]