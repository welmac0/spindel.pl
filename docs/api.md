# API and domain rules

FastAPI exposes interactive documentation at **http://localhost:8000/docs** and the OpenAPI schema at **http://localhost:8000/openapi.json** during native development.

Paths below are backend paths. Through Nginx or the Vite proxy, prefix API requests with `/api`: for example, `/api/listings`. Production frontend routes `/verify` and `/reset-password` handle email links; the backend also provides direct verification and reset entry points.

## Authentication and CSRF

A session lasts seven days. `POST /login` sets `spindel_session` with `HttpOnly`, `SameSite=Lax`, and `Secure` in production; it does not return the raw session token in JSON. Logout revokes the session server-side and removes the cookie.

Before sending a state-changing request, fetch `GET /csrf`, retain its cookie, and send the returned token in `X-CSRF-Token`. The backend compares header and cookie and validates `Origin` when present. Invalid CSRF or an untrusted origin returns `403`.

All `POST`, `PUT`, `PATCH`, and `DELETE` requests require CSRF, including registration, login, and password reset. Session-protected routes return `401` without a valid session. Browser clients must retain cookies across requests; Swagger alone does not automatically perform this CSRF flow.

## Endpoints

| Method and path | Access | Behavior |
| --- | --- | --- |
| `GET /health` | Public | Application/database health; database failure returns `503` |
| `GET /csrf` | Public | Sets the CSRF cookie and returns the token |
| `POST /register` | Public + CSRF | Registration and verification email; neutral `201` for duplicate accounts; delivery failure can return `503` |
| `GET /verify?token=...` | Public | One-time account verification; token valid for seven days |
| `POST /resend-verification` | Public + CSRF | Neutral account-existence message; limit `3/hour` per IP |
| `POST /login` | Public + CSRF | Verified account login; session cookie; limit `10/minute` per IP |
| `POST /logout` | Session + CSRF | Revokes session; `204` |
| `POST /password-reset/request` | Public + CSRF | Neutral `202` for valid requests; limit `3/hour` per IP |
| `GET /reset-password?token=...` | Public | Redirects to the frontend reset page; excluded from OpenAPI |
| `POST /password-reset/confirm` | Public + CSRF | One-time password change and session revocation; limit `10/hour` per IP |
| `GET /listings` | Public | Active listings; `limit` 1–100 and nonnegative `offset` |
| `GET /listings/{listing_id}` | Public | Active listing details; inactive listings return `404` |
| `POST /listings` | Session + CSRF | Creates a listing; at most eight active/pending listings per user |
| `PATCH /listings/{listing_id}` | Owner session + CSRF | Updates listing fields, not status |
| `DELETE /listings/{listing_id}` | Owner session + CSRF | Deletes a listing; `204` |
| `POST /listings/{listing_id}/requests` | Session + CSRF | Requests an exchange on another user's active listing |
| `GET /listings/{listing_id}/requests` | Owner session | Requests for this listing |
| `POST /exchange-requests/{request_id}/confirm` | Listing owner session + CSRF | Confirms exchange; listing becomes `fulfilled` |
| `POST /exchange-requests/{request_id}/reject` | Listing owner session + CSRF | Cancels the request and listing |
| `POST /listings/{listing_id}/cancel` | Owner session + CSRF | Cancels an active or pending listing |
| `GET /me/exchange-requests` | Session | Requests sent and received by the user |
| `GET /me/listings` | Session | The user's listings, including completed listings |
| `GET /enums?lang=pl` | Public | Enum labels; `pl` and `en` supported |
| `GET /stats` | Public | Completed exchange statistics |

Use OpenAPI for exact schemas and validation errors. Rate limits are process-local; production proxy configuration affects which client IP the application sees.

## Domain rules

### Accounts

- University email format: eight digits followed by `@pw.edu.pl`; student index number: six digits.
- Email and student index uniqueness are enforced by database constraints.
- Password length: 8–128 characters.
- Verification tokens are single-use and valid for seven days; reset tokens are single-use and valid for one hour.
- Registration, resend, and reset requests use neutral messages about account existence. Validation, rate limits, or email failures may still produce errors.

### Listings

- `group_have` identifies one current group; `group_want` contains at most five desired groups.
- Desired group numbers are positive, at most two digits, deduplicated, sorted, and stored as comma-separated text in SQLite.
- Current and desired groups must differ.
- A user may have at most eight `active` or `pending` listings.
- Creating a conflicting inverse exchange returns `409` with `conflicting_listing_id`.
- Active listings older than 90 days are marked `stale` during cleanup.

Listing states: `active`, `pending`, `fulfilled`, `stale`, `cancelled`.

### Exchanges

- Only another user's `active` listing can receive a request.
- `active → pending` is atomic, so a second request cannot reserve the same listing.
- After 48 hours, an unconfirmed request expires; cleanup returns the listing to `active` and applies a four-day cooldown to its owner.
- Confirmation sets the request to `confirmed` and listing to `fulfilled`; only then are participant contact details exposed.
- Rejection sets both request and listing to `cancelled`. There is no `rejected` listing state.

Request states: `pending`, `confirmed`, `expired`, `cancelled`.

Cleanup runs in relevant request handlers, not a background timer. These rules describe intended behavior; see [open issues](https://github.com/welmac0/spindel.pl/issues) for known defects.

## Email delivery records

`EmailDelivery` describes a logical delivery and `EmailDeliveryAttempt` an individual attempt. A failed email does not roll back an already persisted registration or exchange. Delivery uses Brevo synchronously; records do not imply an automatic retry worker exists.
