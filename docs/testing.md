# Testing

## Automated checks

From the repository root, after [local setup](../README.md#local-development):

```bash
uv run pytest -q
bash tests/test_external_monitor.sh
```

Backend tests use an isolated in-memory SQLite database and mock email delivery. They must not require production data or a real Brevo API key.

The API suite exercises authentication, session cookies, CSRF/origin checks, verification and reset tokens, listing validation, exchange transitions, expiration/cooldowns, and email delivery records. [Email service tests](../tests/test_email_service.py) cover verification URL construction and missing email configuration. [Monitor tests](../tests/test_external_monitor.sh) exercise state transitions without contacting production or sending live alerts.

To type-check and build the frontend:

```bash
cd frontend
npm ci
npm run build
```

### CI scope

The [CI workflow](../.github/workflows/ci.yml) runs on pushes and pull requests:

| Job | Check |
| --- | --- |
| Backend | Python 3.13, pytest |
| Frontend | Node.js 26, npm clean install, TypeScript/Vite build |
| Shell | Bash syntax and external monitor state-transition tests |
| Compose | Production configuration validation without starting services |

CI creates an empty environment file only to validate Compose references; it does not need production secrets, deploy the application, or verify live email delivery.

### Gaps

Browser E2E tests are not configured. A successful frontend build is not a UI interaction test; successful Compose validation is not a container startup or deployment test. The pipeline does not currently include dependency vulnerability scanning. Follow [Issues](https://github.com/welmac0/spindel.pl/issues) for planned work. No coverage percentage or live availability guarantee is claimed.

## Manual smoke test

Use local synthetic data and accounts you control. Email-dependent flows need a valid Brevo configuration and supported university addresses; no development verification bypass is provided.

1. Register, verify the email link, and confirm login is blocked before verification.
2. Log in, refresh, and log out; inspect `HttpOnly` and check invalid CSRF is rejected.
3. Request a password reset; verify token single use and invalidation of old sessions.
4. Create, filter, edit, and cancel a listing.
5. Request an exchange from a second account; confirm contact details remain hidden until confirmation. Exercise confirmation and rejection separately.
6. Check verification, password reset, and exchange notification emails.
7. Check mobile layout, Polish/English UI, and the maintenance page in a local build.
8. Check health endpoints and database persistence after a container restart.

Expected state transitions are documented in [API and domain rules](api.md). Tests describe intended behavior; check open issues for known defects.

## After deployment

- Confirm backend/frontend containers become `healthy`.
- Check [API health](https://spindel.pl/api/health) and [Nginx health](https://spindel.pl/nginx-health).
- Review backend/frontend/Certbot logs locally without publishing sensitive data.
- Perform a small login and exchange-flow check with controlled accounts only.
- Check backup and monitoring timers separately: a responding website does not prove that backups work.

Never test destructive operations against real users' data. Redact personal information and secrets from bug reports; use the [private reporting policy](../SECURITY.md) for vulnerabilities.
