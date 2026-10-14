# Working agreement

This is a single-author portfolio project, but it follows a team workflow so that the
history is reviewable.

## Flow
1. Every change starts from a GitHub issue assigned to a milestone ([`docs/roadmap.md`](docs/roadmap.md)).
2. Branch from `main`: `<type>/<issue-id>-<slug>`, e.g. `feat/M2-03-getonbrd-ingestion`.
3. Commit with [Conventional Commits](https://www.conventionalcommits.org/):
   `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`.
4. Open a pull request that references the issue (`Closes #N`), fill in the template, and
   merge after CI passes.
5. Architecture changes require a new or updated ADR in [`docs/adr/`](docs/adr/).

## n8n workflows
Change workflows in the n8n editor, then run the export script. Never hand-edit the JSON
in [`workflows/`](workflows/).

## Never commit
Secrets, the real CV or profile, collected offer texts, or database files. See
[`docs/data-governance.md`](docs/data-governance.md).
