from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated, Callable, TypeAlias
import hashlib
from html import escape
import logging
import os
import secrets

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlmodel import Session, select, update

from wymiana_zajec.database import create_db_and_tables, get_session
from wymiana_zajec.email_service import (
    EmailDeliveryError,
    send_exchange_confirmed_email,
    send_exchange_matched_email,
    send_exchange_request_email,
    send_password_reset_email,
    send_verification_email,
)
from wymiana_zajec.models import (
    Listing,
    ListingCreate,
    ListingPublic,
    ListingUpdate,
    PublicMessage,
    ExchangeRequest,
    ExchangeRequestPublic,
    ExchangeStatus,
    ListingStatus,
    User,
    UserCreate,
    UserLogin,
    UserPublic,
    AuthToken,
    EmailDelivery,
    EmailDeliveryAttempt,
    EmailDeliveryStatus,
    VerificationResend,
    PasswordResetRequest,
    PasswordResetConfirm,
    deserialize_group_list,
    serialize_group_list,
)
from wymiana_zajec.translations import CLASS_TYPE_LABELS, MAJOR_LABELS, STATUS_LABELS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("wymiana_zajec")

# Code before yield = app startup, after yield = shutdown (empty here).
# We create the DB tables before the first request arrives.
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield
    
app = FastAPI(lifespan=lifespan)

# Use explicit origins and hosts in production; these defaults support local development and tests.
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
allowed_hosts = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,testserver,testclient",
    ).split(",")
    if host.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

limiter = Limiter(key_func=get_remote_address, headers_enabled=False)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

SessionDep: TypeAlias = Annotated[Session, Depends(get_session)]
bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{salt.hex()}${digest.hex()}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_hex, digest_hex = encoded.split("$", 1)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1
        )
    except (ValueError, TypeError):
        return False
    return secrets.compare_digest(actual, expected)

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: SessionDep,
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = session.exec(
        select(User).where(User.auth_token_hash == token_hash(credentials.credentials))
    ).first()
    if not user or not user.auth_token_expires_at or as_utc(user.auth_token_expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user

CurrentUserDep: TypeAlias = Annotated[User, Depends(get_current_user)]

VERIFICATION_TOKEN_LIFETIME = timedelta(days=7)
PASSWORD_RESET_TOKEN_LIFETIME = timedelta(hours=1)
LISTING_STALE_AFTER = timedelta(days=90)
MAX_OPEN_LISTINGS_PER_USER = 8

def send_logged_email(
    session: Session,
    *,
    recipient_email: str,
    email_type: str,
    sender: Callable[[], None],
) -> bool:
    delivery = EmailDelivery(
        recipient_email=recipient_email,
        email_type=email_type,
        status=EmailDeliveryStatus.pending,
    )
    session.add(delivery)
    session.commit()
    session.refresh(delivery)
    delivery.attempts += 1
    try:
        sender()
    except EmailDeliveryError as error:
        delivery.status = EmailDeliveryStatus.failed
        delivery.last_error = str(error)
        logger.warning("Email delivery failed: type=%s delivery_id=%s", email_type, delivery.id)
        session.add(
            EmailDeliveryAttempt(
                delivery_id=delivery.id,
                attempt_number=delivery.attempts,
                status=EmailDeliveryStatus.failed,
                error=str(error),
            )
        )
        session.add(delivery)
        session.commit()
        return False
    delivery.status = EmailDeliveryStatus.sent
    delivery.sent_at = datetime.now(timezone.utc)
    session.add(
        EmailDeliveryAttempt(
            delivery_id=delivery.id,
            attempt_number=delivery.attempts,
            status=EmailDeliveryStatus.sent,
        )
    )
    session.add(delivery)
    session.commit()
    logger.info("Email delivery sent: type=%s delivery_id=%s", email_type, delivery.id)
    return True

def listing_to_public(listing: Listing) -> ListingPublic:
    data = listing.model_dump()
    data["group_want"] = deserialize_group_list(listing.group_want)
    return ListingPublic.model_validate(data)

def find_inverse_listing(
    session: Session, listing_in: ListingCreate
) -> Listing | None:
    candidates = session.exec(
        select(Listing).where(
            Listing.status == ListingStatus.active,
            Listing.major == listing_in.major,
            Listing.semester == listing_in.semester,
            Listing.subject == listing_in.subject,
            Listing.class_type == listing_in.class_type,
        )
    ).all()
    wanted = set(listing_in.group_want)
    for candidate in candidates:
        candidate_wanted = deserialize_group_list(candidate.group_want)
        if candidate.group_have in wanted and listing_in.group_have in candidate_wanted:
            return candidate
    return None

def find_duplicate_listing(
    session: Session, listing_in: ListingCreate, owner_id: int
) -> Listing | None:
    candidates = session.exec(
        select(Listing).where(
            Listing.owner_id == owner_id,
            Listing.status.in_((ListingStatus.active, ListingStatus.pending)),
            Listing.major == listing_in.major,
            Listing.semester == listing_in.semester,
            Listing.subject == listing_in.subject,
            Listing.class_type == listing_in.class_type,
            Listing.group_have == listing_in.group_have,
        )
    ).all()
    wanted = serialize_group_list(listing_in.group_want)
    return next((listing for listing in candidates if listing.group_want == wanted), None)

def exchange_public(
    exchange_request: ExchangeRequest, session: Session, current_user_id: int | None = None
) -> ExchangeRequestPublic:
    listing = session.get(Listing, exchange_request.listing_id)
    requester = session.get(User, exchange_request.requester_id)
    owner = session.get(User, listing.owner_id) if listing else None
    reveal_contacts = exchange_request.status == ExchangeStatus.confirmed
    return ExchangeRequestPublic(
        id=exchange_request.id,
        listing_id=exchange_request.listing_id,
        requester_id=exchange_request.requester_id,
        status=exchange_request.status,
        created_at=exchange_request.created_at,
        expires_at=exchange_request.expires_at,
        confirmed_at=exchange_request.confirmed_at,
        requester_email=requester.email if reveal_contacts and requester else None,
        owner_email=owner.email if reveal_contacts and owner else None,
        is_owner=current_user_id is not None and owner is not None and owner.id == current_user_id,
        listing=listing_to_public(listing) if listing else None,
    )

@app.get("/health")
def health_check(session: SessionDep):
    try:
        session.exec(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Health check failed")
        raise HTTPException(status_code=503, detail="Service unavailable")
    return {"status": "ok"}

def expire_requests(session: Session) -> None:
    now = datetime.now(timezone.utc)
    requests = session.exec(
        select(ExchangeRequest).where(
            ExchangeRequest.status == ExchangeStatus.pending,
            ExchangeRequest.expires_at <= now,
        )
    ).all()
    changed = False
    for exchange_request in requests:
        exchange_request.status = ExchangeStatus.expired
        listing = session.get(Listing, exchange_request.listing_id)
        owner = session.get(User, listing.owner_id) if listing else None
        if listing and listing.status == ListingStatus.pending:
            listing.status = ListingStatus.active
        if owner:
            owner.listing_cooldown_until = now + timedelta(days=4)
        changed = True
    if changed:
        session.commit()

def expire_stale_listings(session: Session) -> None:
    cutoff = datetime.now(timezone.utc) - LISTING_STALE_AFTER
    stale_listings = session.exec(
        select(Listing).where(
            Listing.status == ListingStatus.active,
            Listing.created_at < cutoff,
        )
    ).all()
    if stale_listings:
        for listing in stale_listings:
            listing.status = ListingStatus.stale
            session.add(listing)
        session.commit()

@app.post("/listings", response_model=ListingPublic)
@limiter.limit("30/hour")
def create_listing(request: Request, listing_in: ListingCreate, session: SessionDep, current_user: CurrentUserDep):
    expire_requests(session)
    expire_stale_listings(session)
    if current_user.listing_cooldown_until and as_utc(current_user.listing_cooldown_until) > datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Listing creation is temporarily unavailable")
    open_listing_count = session.exec(
        select(func.count(Listing.id)).where(
            Listing.owner_id == current_user.id,
            Listing.status.in_((ListingStatus.active, ListingStatus.pending)),
        )
    ).one()
    if open_listing_count >= MAX_OPEN_LISTINGS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You can have at most {MAX_OPEN_LISTINGS_PER_USER} active or pending listings",
        )
    duplicate_listing = find_duplicate_listing(session, listing_in, current_user.id)
    if duplicate_listing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "An identical listing already exists for this user",
                "conflicting_listing_id": duplicate_listing.id,
            },
        )
    inverse_listing = find_inverse_listing(session, listing_in)
    if inverse_listing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "A possible inverse exchange already exists",
                "conflicting_listing_id": inverse_listing.id,
            },
        )
    listing = Listing(
        major=listing_in.major,
        semester=listing_in.semester,
        subject=listing_in.subject,
        class_type=listing_in.class_type,
        group_have=listing_in.group_have,
        group_want=serialize_group_list(listing_in.group_want),
        description=listing_in.description,
        owner_id=current_user.id,
    )
    session.add(listing)
    session.commit()
    # refresh() reloads the object from the DB - after commit() Python
    # doesn't yet know the generated id (the DB assigned it on its side).
    session.refresh(listing)
    return listing_to_public(listing)

@app.get("/listings", response_model=list[ListingPublic])
def read_listings(
    session: SessionDep,
    # le=100 - hard limit, so the client can't pull the whole table
    # in a single request (DoS on a large database).
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    expire_requests(session)
    expire_stale_listings(session)
    # select(Listing) builds a SQL query (SELECT * FROM listing)
    # in a type-safe way, .exec() runs it, .all() returns a list.
    listings = session.exec(
        select(Listing)
        .where(Listing.status == ListingStatus.active)
        .offset(offset)
        .limit(limit)
    ).all()
    return [listing_to_public(listing) for listing in listings]

@app.get("/listings/{listing_id}", response_model=ListingPublic)
def read_listing(listing_id: int, session: SessionDep):
    expire_requests(session)
    expire_stale_listings(session)
    # session.get() is a shortcut for fetching by primary key,
    # returns None if there's no such record.
    listing = session.get(Listing, listing_id)
    if not listing or listing.status != ListingStatus.active:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing_to_public(listing)

@app.patch("/listings/{listing_id}", response_model=ListingPublic)
def update_listing(
    listing_id: int,
    listing_update: ListingUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can update this listing")
    # exclude_unset=True - take only fields actually sent in the request,
    # not the ones with the default None from ListingUpdate. This means
    # the client can't accidentally clear fields it didn't intend to touch.
    update_data = listing_update.model_dump(exclude_unset=True)
    if "group_want" in update_data:
        update_data["group_want"] = serialize_group_list(update_data["group_want"])
    for field, value in update_data.items():
        setattr(listing, field, value)
    if listing.group_have in deserialize_group_list(listing.group_want):
        raise HTTPException(
            status_code=422,
            detail="group_have and group_want cannot be the same",
        )
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return listing_to_public(listing)

# 204 No Content - REST convention for a successful DELETE: there's
# nothing to return (the resource no longer exists), so instead of a
# made-up {"ok": True} we respond with an empty body and a status code
# that speaks for itself.
@app.delete("/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(listing_id: int, session: SessionDep, current_user: CurrentUserDep):
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can delete this listing")
    session.delete(listing)
    session.commit()

# Registration: the client provides email + index_number (both validated
# in UserCreate - see models.py, index_number can't be derived from the
# email). The user gets back a UserPublic with email_verified=False -
# the account isn't active yet until they click the link with the token.
@app.post("/register", response_model=PublicMessage, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register_user(request: Request, user_in: UserCreate, session: SessionDep):
    generic_message = PublicMessage(
        message="If the registration data is valid, check your email for an activation link."
    )
    token = secrets.token_urlsafe(32)
    user = User(
        email=user_in.email,
        index_number=user_in.index_number,
        password_hash=hash_password(user_in.password),
        verification_token_hash=token_hash(token),
        verification_token_expires_at=datetime.now(timezone.utc) + VERIFICATION_TOKEN_LIFETIME,
    )
    session.add(user)
    try:
        # commit(), not an exists()-check before adding - avoids a race
        # condition (two requests at once with the same email). The DB
        # has the unique constraint anyway, so it's the final gatekeeper.
        session.commit()
    except IntegrityError:
        session.rollback()
        return generic_message
    session.refresh(user)
    sent = send_logged_email(
        session,
        recipient_email=user.email,
        email_type="verification",
        sender=lambda: send_verification_email(
            recipient_email=user.email,
            verification_token=token,
            valid_for_days=VERIFICATION_TOKEN_LIFETIME.days,
        ),
    )
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification email could not be sent",
        )
    return generic_message

@app.post("/resend-verification", response_model=PublicMessage)
@limiter.limit("3/hour")
def resend_verification(
    request: Request, resend_request: VerificationResend, session: SessionDep
):
    generic_message = PublicMessage(
        message="If we can send a verification email, you will receive a new link."
    )
    user = session.exec(select(User).where(User.email == resend_request.email)).first()
    if not user:
        return generic_message
    if user.email_verified:
        return generic_message
    now = datetime.now(timezone.utc)
    latest_delivery = session.exec(
        select(EmailDelivery)
        .where(
            EmailDelivery.recipient_email == user.email,
            EmailDelivery.email_type.in_(("verification", "verification_resend")),
        )
        .order_by(EmailDelivery.created_at.desc())
    ).first()
    if (
        latest_delivery
        and latest_delivery.status == EmailDeliveryStatus.sent
        and user.verification_token_expires_at
        and as_utc(user.verification_token_expires_at) > now
    ):
        return generic_message
    token = secrets.token_urlsafe(32)
    user.verification_token_hash = token_hash(token)
    user.verification_token_expires_at = now + VERIFICATION_TOKEN_LIFETIME
    session.add(user)
    session.commit()
    sent = send_logged_email(
        session,
        recipient_email=user.email,
        email_type="verification_resend",
        sender=lambda: send_verification_email(
            recipient_email=user.email,
            verification_token=token,
            valid_for_days=VERIFICATION_TOKEN_LIFETIME.days,
        ),
    )
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification email could not be sent",
        )
    return generic_message

@app.post("/login", response_model=AuthToken)
@limiter.limit("10/minute")
def login_user(request: Request, user_in: UserLogin, session: SessionDep):
    user = session.exec(select(User).where(User.email == user_in.email)).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Email address is not verified")
    access_token = secrets.token_urlsafe(32)
    user.auth_token_hash = token_hash(access_token)
    user.auth_token_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session.add(user)
    session.commit()
    return AuthToken(access_token=access_token)

@app.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/hour")
def request_password_reset(
    request: Request, reset_request: PasswordResetRequest, session: SessionDep
):
    # Always return the same response, whether the account exists or not.
    user = session.exec(
        select(User).where(User.email == reset_request.email)
    ).first()
    if user and user.email_verified:
        raw_token = secrets.token_urlsafe(32)
        user.password_reset_token_hash = token_hash(raw_token)
        user.password_reset_token_expires_at = (
            datetime.now(timezone.utc) + PASSWORD_RESET_TOKEN_LIFETIME
        )
        session.add(user)
        session.commit()
        send_logged_email(
            session,
            recipient_email=user.email,
            email_type="password_reset",
            sender=lambda: send_password_reset_email(
                recipient_email=user.email,
                reset_token=raw_token,
                valid_for_hours=int(PASSWORD_RESET_TOKEN_LIFETIME.total_seconds() // 3600),
            ),
        )
    return {
        "message": "If the account exists, a password reset email has been sent"
    }

@app.get("/reset-password", response_class=RedirectResponse, include_in_schema=False)
def reset_password_page(token: str):
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return RedirectResponse(url=f"{frontend_url}/reset-password?token={token}", status_code=303)

@app.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/hour")
def confirm_password_reset(
    request: Request, reset_confirmation: PasswordResetConfirm, session: SessionDep
):
    user = session.exec(
        select(User).where(
            User.password_reset_token_hash == token_hash(reset_confirmation.token)
        )
    ).first()
    if (
        not user
        or not user.password_reset_token_expires_at
        or as_utc(user.password_reset_token_expires_at) <= datetime.now(timezone.utc)
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user.password_hash = hash_password(reset_confirmation.password)
    user.password_reset_token_hash = None
    user.password_reset_token_expires_at = None
    user.auth_token_hash = None
    user.auth_token_expires_at = None
    session.add(user)
    session.commit()

# GET (not POST) - this is meant to be a plain clickable link from the
# email body, without needing to send a request with JS/body.
@app.get("/verify", response_class=HTMLResponse)
def verify_user(token: str, session: SessionDep):
    user = session.exec(
        select(User).where(User.verification_token_hash == token_hash(token))
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid or already used token")
    if (
        not user.verification_token_expires_at
        or as_utc(user.verification_token_expires_at) <= datetime.now(timezone.utc)
    ):
        raise HTTPException(status_code=410, detail="Verification token has expired")
    user.email_verified = True
    user.verification_token_hash = None
    user.verification_token_expires_at = None
    session.add(user)
    session.commit()
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return f"""
    <!doctype html><html lang="pl"><head><meta charset="utf-8"><title>Email potwierdzony</title>
    <style>body{{font-family:Arial,sans-serif;background:#f5f3ee;color:#26313a;padding:48px}}a{{color:#c94f43}}</style></head>
    <body><h1>Email potwierdzony</h1><p>Potwierdzono. Zaloguj sie na <a href="{escape(frontend_url)}">stronie Spindel</a>.</p></body></html>
    """

# Separate endpoint for enum translations - the frontend queries once,
# gets a code -> label dictionary in the chosen language and maps it locally.
# No need to translate every /listings response individually.
@app.get("/enums")
def get_enum_labels(lang: str = "pl"):
    # Falls back to Polish if someone passes an unsupported language.
    lang = lang if lang in ("pl", "en") else "pl"
    return {
        "major": {k.value: v for k, v in MAJOR_LABELS[lang].items()},
        "class_type": {k.value: v for k, v in CLASS_TYPE_LABELS[lang].items()},
        "status": {k.value: v for k, v in STATUS_LABELS[lang].items()},
    }

@app.get("/stats")
def read_stats(session: SessionDep):
    fulfilled_count = session.exec(
        select(func.count(Listing.id)).where(Listing.status == ListingStatus.fulfilled)
    ).one()
    return {"fulfilled_exchanges": fulfilled_count}

@app.post("/listings/{listing_id}/requests", response_model=ExchangeRequestPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")
def create_exchange_request(
    request: Request, listing_id: int, session: SessionDep, current_user: CurrentUserDep
):
    expire_requests(session)
    listing = session.get(Listing, listing_id)
    if not listing or listing.status != ListingStatus.active:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="The owner cannot request their own listing")
    existing = session.exec(
        select(ExchangeRequest).where(
            ExchangeRequest.listing_id == listing_id,
            ExchangeRequest.requester_id == current_user.id,
            ExchangeRequest.status == ExchangeStatus.pending,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A request already exists")
    result = session.exec(
        update(Listing)
        .where(
            Listing.id == listing_id,
            Listing.owner_id != current_user.id,
            Listing.status == ListingStatus.active,
        )
        .values(status=ListingStatus.pending)
    )
    if result.rowcount != 1:
        session.rollback()
        raise HTTPException(status_code=409, detail="Listing is no longer active")
    exchange_request = ExchangeRequest(
        listing_id=listing_id,
        requester_id=current_user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    session.add(exchange_request)
    session.commit()
    session.refresh(exchange_request)
    send_logged_email(
        session,
        recipient_email=session.get(User, listing.owner_id).email,
        email_type="exchange_request",
        sender=lambda: send_exchange_request_email(
            recipient_email=session.get(User, listing.owner_id).email,
            listing_subject=listing.subject,
            listing_class_type=listing.class_type.value,
        ),
    )
    return exchange_request

@app.get("/listings/{listing_id}/requests", response_model=list[ExchangeRequestPublic])
def read_exchange_requests(
    listing_id: int, session: SessionDep, current_user: CurrentUserDep
):
    expire_requests(session)
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can view requests")
    return session.exec(
        select(ExchangeRequest).where(ExchangeRequest.listing_id == listing_id)
    ).all()

@app.post("/exchange-requests/{request_id}/confirm", response_model=ExchangeRequestPublic)
@limiter.limit("30/hour")
def confirm_exchange_request(
    request: Request, request_id: int, session: SessionDep, current_user: CurrentUserDep
):
    expire_requests(session)
    exchange_request = session.get(ExchangeRequest, request_id)
    if not exchange_request:
        raise HTTPException(status_code=404, detail="Request not found")
    listing = session.get(Listing, exchange_request.listing_id)
    if not listing or listing.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the listing owner can confirm")
    if exchange_request.status != ExchangeStatus.pending:
        raise HTTPException(status_code=409, detail="Request is no longer pending")
    exchange_request.status = ExchangeStatus.confirmed
    exchange_request.confirmed_at = datetime.now(timezone.utc)
    listing.status = ListingStatus.fulfilled
    session.add(exchange_request)
    session.add(listing)
    session.commit()
    session.refresh(exchange_request)
    requester = session.get(User, exchange_request.requester_id)
    send_logged_email(
        session,
        recipient_email=requester.email,
        email_type="exchange_confirmed",
        sender=lambda: send_exchange_matched_email(
            recipient_email=requester.email,
            other_person_email=current_user.email,
            listing_subject=listing.subject,
            listing_class_type=listing.class_type.value,
        ),
    )
    send_logged_email(
        session,
        recipient_email=current_user.email,
        email_type="exchange_matched_owner",
        sender=lambda: send_exchange_matched_email(
            recipient_email=current_user.email,
            other_person_email=requester.email,
            listing_subject=listing.subject,
            listing_class_type=listing.class_type.value,
        ),
    )
    return exchange_public(exchange_request, session)

@app.get("/me/exchange-requests", response_model=list[ExchangeRequestPublic])
def read_my_exchange_requests(session: SessionDep, current_user: CurrentUserDep):
    expire_requests(session)
    requests = session.exec(
        select(ExchangeRequest).where(
            ExchangeRequest.requester_id == current_user.id
        )
    ).all()
    owned_listing_ids = session.exec(
        select(Listing.id).where(Listing.owner_id == current_user.id)
    ).all()
    owner_requests = session.exec(
        select(ExchangeRequest).where(ExchangeRequest.listing_id.in_(owned_listing_ids))
    ).all()
    unique = {request.id: request for request in [*requests, *owner_requests]}
    return [exchange_public(request, session, current_user.id) for request in unique.values()]

@app.get("/me/listings", response_model=list[ListingPublic])
def read_my_listings(session: SessionDep, current_user: CurrentUserDep):
    listings = session.exec(
        select(Listing)
        .where(Listing.owner_id == current_user.id)
        .order_by(Listing.created_at.desc())
    ).all()
    return [listing_to_public(listing) for listing in listings]

@app.post("/listings/{listing_id}/cancel", response_model=ListingPublic)
@limiter.limit("30/hour")
def cancel_listing(request: Request, listing_id: int, session: SessionDep, current_user: CurrentUserDep):
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can cancel this listing")
    if listing.status not in (ListingStatus.active, ListingStatus.pending):
        raise HTTPException(status_code=409, detail="Listing cannot be cancelled")
    listing.status = ListingStatus.cancelled
    pending_requests = session.exec(
        select(ExchangeRequest).where(
            ExchangeRequest.listing_id == listing.id,
            ExchangeRequest.status == ExchangeStatus.pending,
        )
    ).all()
    for exchange_request in pending_requests:
        exchange_request.status = ExchangeStatus.cancelled
        session.add(exchange_request)
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return listing_to_public(listing)

@app.post("/exchange-requests/{request_id}/reject", response_model=ExchangeRequestPublic)
@limiter.limit("30/hour")
def reject_exchange_request(request: Request, request_id: int, session: SessionDep, current_user: CurrentUserDep):
    exchange_request = session.get(ExchangeRequest, request_id)
    if not exchange_request:
        raise HTTPException(status_code=404, detail="Request not found")
    listing = session.get(Listing, exchange_request.listing_id)
    if not listing or listing.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the listing owner can reject")
    if exchange_request.status != ExchangeStatus.pending:
        raise HTTPException(status_code=409, detail="Request is no longer pending")
    exchange_request.status = ExchangeStatus.cancelled
    listing.status = ListingStatus.cancelled
    session.add(exchange_request)
    session.add(listing)
    session.commit()
    session.refresh(exchange_request)
    return exchange_public(exchange_request, session)