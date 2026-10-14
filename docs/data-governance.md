# Data Governance

## 1. Data inventory

| Data | Origin | Contains personal data? | Stored where | In Git? |
|---|---|---|---|---|
| Job offers (title, company, description, URL) | Job boards | Sometimes: recruiter names, e-mails, phone numbers in free text | Local PostgreSQL | **No**; synthetic fixtures only |
| Evaluation labels | Candidate (manual) | No | `evals/labels/` (IDs + labels) | Yes |
| Master CV and application protocol | Candidate | **Yes**: name, phone, e-mail, history | Local file, mounted read-only | **No** |
| Example profile and CV | Authored for this repo | No (fictitious) | `profiles/example/` | Yes |
| Confirmed skills, application statuses | Candidate | Yes (career data) | Local PostgreSQL | No |
| Credentials (Gemini API key, Telegram token, DB password; optional Claude API key) | Candidate | Secret | n8n credential store (encrypted) and `.env` | **No** |
| LLM usage logs | System | No (tokens, costs, request IDs) | Local PostgreSQL | No |

## 2. Source policy

1. **Primary source: Get on Board public API**, which is documented and needs no
   authentication for public job data (see the
   [technical reference](https://api-doc.getonbrd.com/?version=latest)).
2. **Optional adapters** (Trabajando.cl, Computrabajo, Chiletrabajos) are disabled by
   default and must:
   - follow the site's `robots.txt` (checked at startup, with the check date logged);
   - wait ≥ 0.8 s between requests to the same host and back off on HTTP 429/5xx;
   - send an identifiable User-Agent with a contact URL (the repository);
   - fetch only public pages, without logins or CAPTCHA circumvention.
3. **Never collected:** sites that need authentication or forbid automated access
   (LinkedIn, Indeed, Laborum). For these the digest contains pre-built search links only.
4. Each adapter's terms of use are reviewed before the adapter is enabled, and the review
   date is recorded in the adapter's docstring.

## 3. Third-party content

Offer descriptions are third-party content. They are used locally for matching and
evaluation and are **not redistributed**: they never enter Git, release artefacts or
published reports. Reports quote at most short field values (for example, a contract
type), never full descriptions.

## 4. Personal data

- **Candidate data** is processed by and for the candidate, who is the data subject and
  the operator. It is never committed. A pre-commit hook and a CI scan (M1) reject files
  that match the master CV's path and known personal identifiers.
- **Third-party personal data in offers** (recruiter e-mails and phone numbers) is
  **redacted** by `/normalize` before storage in `description_text` and before any LLM
  call. The unredacted `raw` payload is kept only for the retention period.
- **Retention:** offer texts are purged after 180 days, and labels and features are kept
  (see [`data-model.md`](data-model.md)).
- **Regulatory context (Chile):** Law 19.628 on the protection of private life applies. Law
  21.719, which strengthens data-protection obligations, is scheduled to take effect in
  December 2026 (to be verified against the official text before M2). This is a personal,
  non-commercial tool, but the design follows data minimisation regardless.

## 5. LLM data flow

Provider policy per task: [ADR-0007](adr/0007-zero-cost-provider-agnostic-llm.md).

| Task | Provider | Sent | Never sent |
|---|---|---|---|
| Requirement extraction | Gemini API **free tier** (local fallback) | Redacted offer title and description, which are public data | Any candidate data |
| CV adaptation | **Local model (Ollama)**; never leaves the machine | Master CV, protocol, confirmed skills, redacted offer | n/a, because the data stays local |
| CV adaptation, manual mode | Candidate pastes a prompt bundle into a chat app of their choice | Whatever the candidate decides to paste | Not automated |

**Why the split.** Under the Gemini API's unpaid-service terms, inputs and outputs may be
used to improve Google's products and may be read by human reviewers. The terms instruct
users not to submit personal information
([Gemini API terms](https://ai.google.dev/gemini-api/terms)). The router therefore sends
only public, contact-redacted offer text to the free tier. Any route that would send
personal data to an unpaid service is rejected by policy, and that rule is unit-tested.

If the candidate uses manual mode with a consumer chat app, that app's own data settings
(for example, activity and training settings) apply. The candidate reviews them before
pasting a CV.

Prompts and responses are stored locally in `cv_adaptations` / `offer_features`, so
every output is auditable.

## 6. Secrets management

- Secrets live in the n8n credential store, which is encrypted with `N8N_ENCRYPTION_KEY`.
  The key is backed up **outside** the repository; without it, credentials cannot be
  restored.
- `.env` is git-ignored and `.env.example` documents the variables with dummy values.
- Workflow exports carry credential references, never secret values (n8n CLI behaviour;
  verified in M1). `export:credentials --decrypted` is never used inside the repository.
- The Telegram bot answers only an allow-listed private `chat_id`.

## 7. Access and exposure

All services bind to a private Docker network. Only n8n's editor port is published to
`localhost`. Ollama runs on the host and is not exposed to the LAN. It must still be reachable from
the containers through `host.docker.internal`; the exact binding for Docker Desktop vs
Colima is verified in M1-07. A tunnel for Telegram webhooks or MCP over HTTP, if one is used, is
authenticated and documented in `infra/README.md`.
