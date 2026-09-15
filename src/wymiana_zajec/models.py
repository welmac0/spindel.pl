from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import re

from pydantic import model_validator
from sqlmodel import Field, SQLModel

class Major(str, Enum):
    mat = "mat"
    iad = "iad"
    iisi = "iisi"
    mad = "mad"
    cs = "cs"
    
class ClassType(str, Enum):
    cwi = "tutorial"
    lab = "labs"
    pro = "project"
    
class ListingStatus(str, Enum):
    active = "active"
    pending = "pending"
    fulfilled = "fulfilled"
    stale = "stale"
    cancelled = "cancelled"

class ExchangeStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    expired = "expired"
    cancelled = "cancelled"

class EmailDeliveryStatus(str, Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"

# Shared fields for Listing/Create/Public, so we don't repeat them
# three times. Each of these models inherits from the same set,
# so DB columns and API fields always stay in sync.
#
# ge/le and min_length/max_length also end up in the OpenAPI schema
# (Swagger shows the client the limits), and validation runs before
# anything hits the database - without this SQLite would accept an
# arbitrarily long string or a negative semester without complaint.
def normalize_group_list(groups: list[str]) -> list[str]:
    normalized = set()
    for group in groups:
        value = group.strip()
        if not value.isdigit() or int(value) <= 0:
            raise ValueError("Groups must contain positive numbers")
        normalized.add(str(int(value)))
    if not normalized:
        raise ValueError("At least one wanted group is required")
    return sorted(normalized, key=int)

def serialize_group_list(groups: list[str]) -> str:
    return ",".join(normalize_group_list(groups))

def deserialize_group_list(groups: str) -> list[str]:
    return normalize_group_list(groups.split(","))

class ListingFields(SQLModel):
    major: Major
    # 1-14 with room for combined programs (bachelor's + master's) -
    # adjust if USOS uses a different real range.
    semester: int = Field(ge=1, le=14)
    subject: str = Field(min_length=1, max_length=200)
    class_type: ClassType
    group_have: str = Field(min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=1000)

class Listing(ListingFields, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    group_want: str = Field(min_length=1, max_length=200)

    status: ListingStatus = ListingStatus.active
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Request body for POST. Deliberately WITHOUT id/status/created_at -
# these are fields the server sets exclusively. If the client could
# send them (like when accepting a bare Listing), they could force
# status="closed" or fake created_at (mass assignment / OWASP A04 -
# insecure design).
class ListingCreate(ListingFields):
    group_want: list[str]

    @model_validator(mode="after")
    def validate_groups(self):
        self.group_want = normalize_group_list(self.group_want)
        if self.group_have in self.group_want:
            raise ValueError("group_have and group_want cannot be the same")
        return self

# Response model for GET/POST/PATCH. Currently identical to Listing,
# but exists as a separate type because eventually (after adding User)
# this is where we'll hide the listing owner's data until the exchange
# is accepted - without changing the endpoints, just by editing this model.
class ListingPublic(ListingFields):
    id: int
    owner_id: int
    group_want: list[str]
    status: ListingStatus
    created_at: datetime

# Separate model (no table=True) for PATCH: all fields optional with
# default=None, so the client can send only some fields. Listing has
# them required (since that's how they look in the DB), so it can't
# be used directly as the body for a partial update.
class ListingUpdate(SQLModel):
    major: Optional[Major] = None
    semester: Optional[int] = Field(default=None, ge=1, le=14)
    subject: Optional[str] = Field(default=None, min_length=1, max_length=200)
    class_type: Optional[ClassType] = None
    group_have: Optional[str] = Field(default=None, min_length=1, max_length=50)
    group_want: Optional[list[str]] = None
    description: Optional[str] = Field(default=None, max_length=1000)
    # Both fields are optional here, so we only check when the client
    # actually sent both groups at once - a PATCH of group_have alone
    # has nothing to compare against group_want.
    @model_validator(mode="after")
    def check_groups_differ(self):
        if (
            self.group_have is not None
            and self.group_want is not None
            and self.group_have in normalize_group_list(self.group_want)
        ):
            raise ValueError("group_have and group_want cannot be the same")
        return self

# PW email is an 8-digit login (unrelated to the index number - these
# are two different identifiers). The index number has a different
# length and CANNOT be derived from the email, so the user provides it
# separately - we treat it as a self-declaration (verifying it against
# USOS is a separate topic for later).
PW_EMAIL_LOGIN_LENGTH = 8
INDEX_NUMBER_LENGTH = 6
PW_EMAIL_PATTERN = re.compile(rf"^\d{{{PW_EMAIL_LOGIN_LENGTH}}}@pw\.edu\.pl$")

class UserBase(SQLModel):
    # unique+index: the DB itself rejects duplicates (constraint), and
    # index speeds up lookups during login/verification.
    email: str = Field(unique=True, index=True, max_length=255)
    index_number: str = Field(unique=True, index=True, max_length=INDEX_NUMBER_LENGTH)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    password_hash: str
    email_verified: bool = False
    # Only the hash is stored. The raw token exists only in the email link.
    verification_token_hash: Optional[str] = Field(default=None, index=True)
    verification_token_expires_at: Optional[datetime] = None
    auth_token_hash: Optional[str] = Field(default=None, index=True)
    auth_token_expires_at: Optional[datetime] = None
    password_reset_token_hash: Optional[str] = Field(default=None, index=True)
    password_reset_token_expires_at: Optional[datetime] = None
    listing_cooldown_until: Optional[datetime] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Request body for registration: email + index_number provided directly
# by the user (index_number can't be derived from the email).
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_pw_email(self):
        if not PW_EMAIL_PATTERN.match(self.email):
            raise ValueError(
                f"Email must be in the format {PW_EMAIL_LOGIN_LENGTH}-digit-login@pw.edu.pl"
            )
        if not self.index_number.isdigit() or len(self.index_number) != INDEX_NUMBER_LENGTH:
            raise ValueError(f"Index number must have {INDEX_NUMBER_LENGTH} digits")
        return self


# Response model - deliberately without verification_token (it has no
# business leaking to the client - anyone who learns it could verify
# someone else's account before the owner clicks the link in their email).
class UserPublic(UserBase):
    id: int
    index_number: str
    email_verified: bool
    created_at: datetime

class UserLogin(SQLModel):
    email: str
    password: str

class VerificationResend(SQLModel):
    email: str

class PasswordResetRequest(SQLModel):
    email: str

class PasswordResetConfirm(SQLModel):
    token: str
    password: str = Field(min_length=8, max_length=128)

class AuthToken(SQLModel):
    access_token: str
    token_type: str = "bearer"

class ExchangeRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    listing_id: int = Field(foreign_key="listing.id", index=True)
    requester_id: int = Field(foreign_key="user.id", index=True)
    status: ExchangeStatus = ExchangeStatus.pending
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    confirmed_at: Optional[datetime] = None

class ExchangeRequestPublic(SQLModel):
    id: int
    listing_id: int
    requester_id: int
    status: ExchangeStatus
    created_at: datetime
    expires_at: datetime
    confirmed_at: Optional[datetime]
    requester_email: Optional[str] = None
    owner_email: Optional[str] = None
    is_owner: bool = False
    listing: Optional[ListingPublic] = None

class EmailDelivery(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    recipient_email: str = Field(index=True, max_length=255)
    email_type: str = Field(index=True, max_length=100)
    status: EmailDeliveryStatus = EmailDeliveryStatus.pending
    attempts: int = 0
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None

class EmailDeliveryAttempt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    delivery_id: int = Field(foreign_key="emaildelivery.id", index=True)
    attempt_number: int
    status: EmailDeliveryStatus
    error: Optional[str] = None
    attempted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))