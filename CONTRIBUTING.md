# Contributing

Use [GitHub Issues](https://github.com/welmac0/spindel.pl/issues) for bugs and proposals. For vulnerabilities, follow [the security policy](SECURITY.md) instead of opening a public issue.

## Development

Follow the [README](README.md#local-development) for native setup. Use `uv` for Python dependencies and commit corresponding lockfile changes. Frontend dependencies use npm and its lockfile.

Use local, synthetic data only. Never commit credentials, environment files containing secrets, databases, backups, session tokens, or user information. The tracked configuration template must contain placeholders only.

## Checks

From the repository root:

```bash
uv run pytest -q
bash tests/test_external_monitor.sh
```

For frontend changes, run `npm ci` and `npm run build` in the frontend directory. Additional checks and manual flows are described in [testing](docs/testing.md).

The project is currently developed independently and external code contributions are not being accepted yet. Bug reports and feedback are welcome. Maintainer commits directly to `main` are supported. Deployments are separate, manual operations and require successful CI.

## Licensing

All rights are reserved as described in [LICENSE](LICENSE). Public access does not grant general reuse rights. An open-source license may be considered later.