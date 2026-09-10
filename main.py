from contextlib import asynccontextmanager
from typing import Annotated
import secrets

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from database import create_db_and_tables, get_session
from models import (
    Listing,
    ListingCreate,
    ListingPublic,
    ListingUpdate,
    User,
    UserCreate,
    UserPublic,
)
from translations import CLASS_TYPE_LABELS, MAJOR_LABELS, STATUS_LABELS

# Code before yield = app startup, after yield = shutdown (empty here).
# We create the DB tables before the first request arrives.
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield
    
app = FastAPI(lifespan=lifespan)

SessionDep = Annotated[Session, Depends(get_session)]

@app.post("/listings", response_model=ListingPublic)
def create_listing(listing_in: ListingCreate, session: SessionDep):
    # model_validate translates ListingCreate (without id/status/created_at)
    # into a full Listing - missing fields get defaults from the model (table=True).
    listing = Listing.model_validate(listing_in)
    session.add(listing)
    session.commit()
    # refresh() reloads the object from the DB - after commit() Python
    # doesn't yet know the generated id (the DB assigned it on its side).
    session.refresh(listing)
    return listing

@app.get("/listings", response_model=list[ListingPublic])
def read_listings(
    session: SessionDep,
    # le=100 - hard limit, so the client can't pull the whole table
    # in a single request (DoS on a large database).
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    # select(Listing) builds a SQL query (SELECT * FROM listing)
    # in a type-safe way, .exec() runs it, .all() returns a list.
    return session.exec(select(Listing).offset(offset).limit(limit)).all()

@app.get("/listings/{listing_id}", response_model=ListingPublic)
def read_listing(listing_id: int, session: SessionDep):
    # session.get() is a shortcut for fetching by primary key,
    # returns None if there's no such record.
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing

@app.patch("/listings/{listing_id}", response_model=ListingPublic)
def update_listing(listing_id: int, listing_update: ListingUpdate, session: SessionDep):
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    # exclude_unset=True - take only fields actually sent in the request,
    # not the ones with the default None from ListingUpdate. This means
    # the client can't accidentally clear fields it didn't intend to touch.
    update_data = listing_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(listing, field, value)
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return listing

# 204 No Content - REST convention for a successful DELETE: there's
# nothing to return (the resource no longer exists), so instead of a
# made-up {"ok": True} we respond with an empty body and a status code
# that speaks for itself.
@app.delete("/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(listing_id: int, session: SessionDep):
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    session.delete(listing)
    session.commit()

# Registration: the client provides email + index_number (both validated
# in UserCreate - see models.py, index_number can't be derived from the
# email). The user gets back a UserPublic with email_verified=False -
# the account isn't active yet until they click the link with the token.
@app.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, session: SessionDep):
    token = secrets.token_urlsafe(32)
    user = User.model_validate(user_in, update={"verification_token": token})
    session.add(user)
    try:
        # commit(), not an exists()-check before adding - avoids a race
        # condition (two requests at once with the same email). The DB
        # has the unique constraint anyway, so it's the final gatekeeper.
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email or index number already exists",
        )
    session.refresh(user)
    # TODO: real SMTP. For now the verification link only goes to the
    # server log, so the flow can be tested without mail configuration.
    # The token does NOT come back in the API response - it's a secret
    # that must only reach the email owner's inbox.
    print(f"[DEV] Verification link for {user.email}: /verify?token={token}")
    return user

# GET (not POST) - this is meant to be a plain clickable link from the
# email body, without needing to send a request with JS/body.
@app.get("/verify", response_model=UserPublic)
def verify_user(token: str, session: SessionDep):
    user = session.exec(select(User).where(User.verification_token == token)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid or already used token")
    user.email_verified = True
    user.verification_token = None
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

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