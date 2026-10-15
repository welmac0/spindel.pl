# Security policy

## Reporting a vulnerability

Do not include vulnerabilities, exploit details, credentials, tokens, or user data in public issues.

Use GitHub's **Security → Report a vulnerability** on [this repository](https://github.com/welmac0/spindel.pl/security/advisories/new) if private vulnerability reporting is enabled. If it is unavailable, use the contact details published in the live application's privacy policy and request a private reporting channel before sending sensitive details.

Include the affected component or revision, a minimal reproduction using synthetic data, and the potential impact. Do not test against other users' accounts, disrupt production, or retrieve real user data.

## Maintenance scope

Security fixes target the current `main` branch; no older release support policy or response-time guarantee is established. Deployment of a fix is a separate operation from merging it.

See [security design and limitations](docs/security.md) for implemented controls. Repository settings such as private vulnerability reporting, secret scanning, and deployment approvals must be configured separately on GitHub; the presence of this policy does not enable them.