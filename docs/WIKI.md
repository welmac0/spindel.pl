# Spindel documentation

Start with the [README](../README.md) for an overview and native local setup.

| Topic | Document |
| --- | --- |
| Components, exchange lifecycle, configuration, Docker development | [Architecture](architecture.md) |
| Endpoints, authentication, validation, state transitions | [API and domain rules](api.md) |
| Security controls and limitations | [Security design](security.md) |
| Automated checks and manual smoke tests | [Testing](testing.md) |
| Production deployment, backups, monitoring, recovery | [Operations](operations.md) |
| Development and contribution workflow | [Contributing](../CONTRIBUTING.md) |
| Private vulnerability reports | [Security policy](../SECURITY.md) |

## Sources of truth

- Current tasks and priorities: [GitHub Issues](https://github.com/welmac0/spindel.pl/issues). TODO files are supplementary historical and operational checklists.
- Exact request/response schemas: the running API's `/docs` and `/openapi.json`, together with source code and tests.
- Deployment behavior: the checked-in workflows and infrastructure configuration. Live server configuration must be verified independently.

Update the relevant document alongside changes to API behavior, security, tests, deployment, or backups. Additional maintainer notes remain in [notes-how2](notes-how2/); some are in Polish and may describe a particular workstation. [Agent context](LLM_CONTEXT.md) is a separate maintainer aid, not the primary project documentation.
