# ADR-0006: Versioning n8n workflows in Git

- **Status:** Accepted (to be verified in M1-03)
- **Date:** 2026-10-14

## Context
n8n stores workflows in its database. A portfolio repository must show the workflows,
review their changes and restore them on a clean instance, without leaking credentials.

## Decision
Export with the n8n CLI: `n8n export:workflow --backup --output=workflows/`. `--backup`
is documented as `--all --pretty --separate`, which writes one pretty-printed JSON file
per workflow. Import with `n8n import:workflow --separate --input=workflows/`. A
normalisation step strips volatile fields (timestamps, execution metadata) so that diffs
show only real changes. Credentials are never exported to the repository.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Manual UI download | No tooling | Error-prone; inconsistent formatting |
| n8n built-in Git source control | Integrated | Licensing/edition restrictions for self-hosted use (to be verified) |
| **CLI export + script** | Free, scriptable, CI-friendly | Requires running inside the n8n container |

## Consequences
- Imported workflows are inactive by default and must be activated deliberately.
- Restoring credentials needs the same `N8N_ENCRYPTION_KEY` (backed up outside Git).
- CI validates that exported JSON contains no secret-looking values.

## References
- n8n CLI commands: https://docs.n8n.io/hosting/cli-commands/
