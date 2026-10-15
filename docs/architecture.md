# Architecture and setup

## Product scope

Spindel coordinates class group exchanges between Warsaw University of Technology students. A verified student publishes a listing; another student requests an exchange; the owner confirms before contact details are shared. Enrollment changes still happen outside Spindel.

## Components

- **Frontend:** React + TypeScript + Vite; Nginx serves the production static build.
- **Backend:** FastAPI + SQLModel, served by Uvicorn.
- **Database:** SQLite; native development uses a file in the repository root, while Compose uses the external volume `docker_wymiana_data`.
- **Routing and TLS:** Nginx forwards `/api` to the backend and terminates HTTPS; Certbot renews certificates.
- **Email:** Brevo Transactional API.
- **Hosting:** Docker Compose on a single Ubuntu VPS at Hetzner.

See the component diagram in the [README](../README.md#architecture).

## Exchange lifecycle

1. A student registers with a university email and verifies ownership through an email link.
2. The student publishes a listing describing the current and desired groups.
3. Another student requests an exchange. An atomic `active → pending` transition prevents a second request from reserving the same listing.
4. The owner confirms or rejects the request.
5. Confirmation marks the listing `fulfilled` and exposes contact details to the participants. Rejection cancels the request and listing.
6. An unconfirmed request expires after 48 hours; the listing returns to `active` and the owner receives a four-day cooldown.

Expiration cleanup is performed by application request handlers, not by a dedicated scheduler. See [API rules](api.md) for access controls and states. Known bugs and improvements are tracked in [Issues](https://github.com/welmac0/spindel.pl/issues).

## Code map

| File | Responsibility |
| --- | --- |
| [main.py](../src/wymiana_zajec/main.py) | Routes, authentication, rate limiting, exchange logic, email delivery records |
| [models.py](../src/wymiana_zajec/models.py) | SQLModel tables, DTOs, enums, validation |
| [database.py](../src/wymiana_zajec/database.py) | SQLite engine, sessions, initial table creation |
| [email_service.py](../src/wymiana_zajec/email_service.py) | Brevo integration and email content |
| [translations.py](../src/wymiana_zajec/translations.py) | Polish and English enum labels |
| [main.tsx](../frontend/src/main.tsx) | React application |

Infrastructure is in [docker](../docker/), operational scripts in [scripts](../scripts/), and tests in [tests](../tests/).

## Configuration

Copy [.env.example](../.env.example) to a local `.env` before starting the backend. Existing process environment variables take precedence over dotenv values. Restart the backend after changes.

| Variable | Purpose |
| --- | --- |
| `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME` | Email credentials and sender identity; Brevo must accept the sender |
| `APP_BASE_URL` | Base URL for verification/reset email links: frontend in production, backend in native development |
| `FRONTEND_URL` | Browser destination for frontend links and redirects |
| `ALLOWED_ORIGINS` | Comma-separated browser origins, including scheme and port |
| `ALLOWED_HOSTS` | Comma-separated request hostnames, without scheme or port |
| `SESSION_COOKIE_SECURE` | `false` for local HTTP; `true` for production HTTPS |
| `DATABASE_PATH` | Optional SQLite location, set in the process environment before startup; defaults to a file in the repository root |
| `ALERT_EMAIL` | Recipient used by monitoring scripts, not by normal application startup |
| `VITE_MAINTENANCE` | Frontend build-time flag, not a backend runtime setting |

The template targets **native development** on `http://localhost:5173`, with the backend on `http://localhost:8000`. Follow the [README](../README.md#local-development) for commands. No database migration step is needed for an empty database: startup creates missing tables. It does not migrate existing ones.

Native startup currently imports the database module before loading dotenv, so putting `DATABASE_PATH` only in the local environment file does not override the database location. Set it in the process environment instead. Compose injects it before startup and is unaffected.

Without Brevo credentials, startup and non-email functionality remain available, but registration/verification and recovery cannot complete normally. There is no mock email switch. Tests replace email delivery rather than using live credentials.

For native Vite, set `VITE_MAINTENANCE` in the process environment or the frontend's local environment file. Vite does not automatically read the repository-root `.env`. The production Compose build forwards the flag; a rebuilt frontend is required to change deployed behavior.

### Docker development

The [development Compose configuration](../docker/compose.yaml) uses frontend port **5175**, backend port **8000**, and a pre-existing external SQLite volume. Create a local volume named `docker_wymiana_data` before the first start, then build and start that Compose configuration. Do not connect development containers to production data.

When using this mode, set `FRONTEND_URL` and `ALLOWED_ORIGINS` to `http://localhost:5175`; keep `APP_BASE_URL=http://localhost:8000`. Both Compose variants use the same volume name, so they are not independent environments on one Docker host unless explicitly separated. Avoid destructive volume cleanup commands; never delete the database volume to resolve an application problem.

### Production

Use the public HTTPS origin for frontend/origin settings. In production, `APP_BASE_URL=https://spindel.pl` points email links to the frontend's verification/reset pages; the frontend calls the API as needed. Native development instead uses backend email entry points at port 8000. The [production Compose configuration](../docker/compose.prod.yaml) forces secure cookies and does not publish the backend port. See [operations](operations.md).

## Trade-offs and limitations

- A single VPS is simple to operate but is a host-level single point of failure.
- SQLite avoids a separate database service but constrains concurrent writes and scaling options.
- `create_all()` creates tables, not schema migrations. Schema changes require an explicit compatibility and recovery plan.
- Rate limiting is process-local; multiple workers/instances would require a shared strategy.
- Email delivery is synchronous with no queue or automated retry worker.
- Expiration cleanup is request-driven rather than guaranteed at an exact wall-clock deadline.

These are current constraints, not promises of future infrastructure changes. Security details are in [security](security.md); automated and manual validation are in [testing](testing.md).
