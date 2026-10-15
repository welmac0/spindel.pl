# Security design

For private vulnerability reports, see [SECURITY.md](../SECURITY.md). This document describes implemented controls and limitations, not a security certification.

## Application controls

- Passwords are hashed with `hashlib.scrypt` and a random salt.
- Session, email verification, and password reset tokens are generated cryptographically; the database stores hashes rather than raw tokens.
- Browser sessions use `spindel_session`: `HttpOnly`, `SameSite=Lax`, seven-day lifetime. Production Compose sets `SESSION_COOKIE_SECURE=true`.
- All `POST`, `PUT`, `PATCH`, and `DELETE` requests require double-submit CSRF protection: `spindel_csrf` cookie plus `X-CSRF-Token` header. The backend also validates `Origin` when present.
- Logout invalidates the current server-side session; a password reset revokes the user's existing sessions.
- Registration, verification resend, and reset request responses use neutral account-existence messages. Input validation, rate limits, and delivery errors can still produce other responses.
- Protected operations validate authentication, ownership where applicable, and business state.
- Exchange contact details are disclosed only after confirmation.
- Verification/reset tokens travel through email links; frontend handling removes tokens it consumes from the address bar. Do not copy links, tokens, or sensitive query strings into logs or issues.

## Infrastructure controls

The [production Compose configuration](../docker/compose.prod.yaml) sets read-only filesystems, dropped capabilities, `no-new-privileges`, resource limits, and explicit writable mounts for the application containers. The backend port is not published.

[Nginx production configuration](../docker/nginx.prod.conf) handles HTTPS, HTTP-to-HTTPS redirects, HSTS, CSP, framing restrictions, `X-Content-Type-Options`, and `Referrer-Policy`.

Host controls must be configured independently: key-only SSH, disabled password authentication, and a firewall allowing public HTTP/HTTPS plus necessary administrative access. CORS and allowed host validation are **not** a network firewall. Restricting SSH must account for the deployment runner's access.

## Secrets and data

- Keep runtime secrets outside Git; [.env.example](../.env.example) contains placeholders only.
- Keep SSH deployment credentials in GitHub secrets. Production environment secrets can be gated by environment rules; a workflow referencing an environment does not itself configure approval requirements.
- Configure default read-only Actions token permissions, external contributor workflow approvals, and deployment branch restrictions on GitHub.
- Avoid exposing passwords, raw tokens, environment file contents, user records, database files, or backups in diagnostics, screenshots, logs, and public reports.
- Use synthetic data for screenshots and tests. If a real credential enters Git history, revoke it; deleting the file is not sufficient.

Repository settings and live host state cannot be inferred from the checked-in configuration alone.

## Known limitations

- Rate limiting is in memory and is not shared between processes or instances.
- The single VPS is a host-level single point of failure.
- SQLite and the lack of automated schema migrations require careful handling of data and schema changes.
- Email delivery depends on an external service and has no asynchronous retry queue.
- Application tests and health checks are not a penetration test or proof of availability.

See [operations](operations.md) for backup and recovery responsibilities, and [testing](testing.md) for current checks.
