# Roadmap

Effort assumes part-time dedication (about 10–12 h/week). Each milestone ends in a state
that can be demonstrated on its own. **The MVP closes at M4**; M5–M7 add the
differentiating capabilities (guardrail, evaluation, MCP).

| Milestone | Estimated effort | Cumulative | Demonstrable outcome |
|---|---|---|---|
| M0 Design | done | — | Design documentation and backlog |
| M1 Local platform | 1 week | 1 | Healthy stack from a clean clone; workflows versioned |
| M2 Ingestion | 1.5 weeks | 2.5 | Offers flowing daily into PostgreSQL |
| M3 Enrichment & scoring | 1.5 weeks | 4 | Scored offers with rules + LLM features |
| M4 Notifications (MVP) | 1 week | 5 | Daily Telegram digest with actions and tracking |
| M5 CV agent + guardrail | 1.5 weeks | 6.5 | Validated CV sections on demand |
| M6 Evaluation & observability | 2 weeks | 8.5 | Results report with CIs and costs |
| M7 MCP & case study | 1 week | 9.5 | MCP tools, demo, written case study, v1.0.0 |

The table below is the source of truth for the GitHub issues. The `Done when` column is
the acceptance criterion copied into each issue.

## M0 Design

| ID | Issue | Done when | Labels |
|---|---|---|---|
| M0-01 | Design documentation and ADRs | Architecture, process analysis, data model, evaluation plan, governance, roadmap and ADR-0001…0006 are merged | type:docs |
| M0-02 | Repository conventions | Labels, milestones, issue/PR templates and CONTRIBUTING are in place | type:docs |

## M1 Local platform

| ID | Issue | Done when | Labels |
|---|---|---|---|
| M1-01 | Docker Compose for n8n + PostgreSQL | `docker compose up` reaches healthy state; image versions pinned; n8n uses PostgreSQL | type:infra, area:infra |
| M1-02 | Environment and secrets handling | `.env.example` documented; `N8N_ENCRYPTION_KEY` backup procedure written in `infra/README.md` | type:infra, area:infra |
| M1-03 | Workflow export/import scripts | `scripts/export_workflows.sh` and `import_workflows.sh` use the n8n CLI (`--backup`); exported JSON contains no secrets | type:infra, area:n8n |
| M1-04 | CI pipeline | GitHub Actions run lint, workflow JSON validation, secret scan and a compose smoke test on every PR | type:infra, area:infra |
| M1-05 | Pre-commit hooks | ruff, a secret scan and a personal-data path guard run locally before commit | type:infra, area:infra |
| M1-06 | Spike: verify n8n capabilities for the pinned version | MCP Server Trigger transports, Evaluations licensing, and how the Anthropic node implements structured output are documented, and ADR-0004 is updated | type:spike, area:n8n, area:llm |

## M2 Ingestion

| ID | Issue | Done when | Labels |
|---|---|---|---|
| M2-01 | Database schema v1 | Migrations create `runs`, `run_sources`, `offers`; applied automatically on startup | type:feature, area:db |
| M2-02 | matcher-service skeleton | FastAPI with Pydantic models, `/health`, `/normalize` (including PII redaction), tests ≥ 90 % line coverage on the module | type:feature, area:service |
| M2-03 | WF-01 Get on Board ingestion | Scheduled workflow pages through queries and categories, upserts offers and records per-source counts | type:feature, area:n8n |
| M2-04 | Cross-source deduplication | `/dedupe` ported from the As-Is with tests; duplicates linked through `duplicate_of` | type:feature, area:service |
| M2-05 | Optional source adapters | Adapters behind feature flags; `robots.txt` check, rate limiting and synthetic-fixture tests | type:feature, area:service |
| M2-06 | Measure the arrival rate | Two weeks of runs summarised (new offers/day, per source); cost estimate in ADR-0004 updated | type:spike, area:llm |

## M3 Enrichment & scoring

| ID | Issue | Done when | Labels |
|---|---|---|---|
| M3-01 | Port rule-based extraction | `/extract/rules` reproduces As-Is outputs on an archived input set (parity tests) | type:feature, area:service |
| M3-02 | Port scoring | `/score` returns score, breakdown and discard reasons; profile is configuration-driven | type:feature, area:service |
| M3-03 | Extraction schema and prompt v1 | Versioned JSON Schema and prompt in the repository; validated on the development set | type:feature, area:llm |
| M3-04 | WF-02 LLM structured extraction | Pre-filtered offers are extracted with schema-valid output; every call logged in `llm_calls` | type:feature, area:n8n, area:llm |
| M3-05 | Hybrid merge and feature storage | Merge policy implemented; `offer_features` append-only per extractor and version | type:feature, area:service, area:db |
| M3-06 | Fictitious example profile | `profiles/example/` contains a realistic, fully fictitious profile and CV used by tests and demo | type:docs |

## M4 Notifications (MVP)

| ID | Issue | Done when | Labels |
|---|---|---|---|
| M4-01 | Telegram bot setup | Bot answers only the allow-listed private chat; setup documented | type:feature, area:n8n |
| M4-02 | WF-03 daily digest | Top-N new offers above threshold are delivered with score, key facts and links | type:feature, area:n8n |
| M4-03 | WF-04 actions and application tracking | Buttons update `applications` with valid status transitions; idempotent on repeated taps | type:feature, area:n8n, area:db |
| M4-04 | WF-08 error alerts | Any workflow failure produces an alert with workflow, node and run ID | type:feature, area:n8n |
| M4-05 | MVP quickstart and demo | README quickstart verified from a clean clone; screenshots or a GIF of the digest | type:docs |

## M5 CV agent + guardrail

| ID | Issue | Done when | Labels |
|---|---|---|---|
| M5-01 | CV output schema | JSON Schema for sections, keywords, gaps and match before/after; LaTeX sections stay within the 1-page constraints | type:feature, area:llm |
| M5-02 | Guardrail validator | `/validate/cv` traces each skill and claim to the master CV or the confirmed skills; adversarial test cases included | type:feature, area:service |
| M5-03 | WF-05 CV adaptation | Retry once on violations; unresolved violations are delivered as flagged, never silently | type:feature, area:n8n, area:llm |
| M5-04 | Confirm-a-gap flow | The candidate can confirm a gap with evidence from Telegram; stored in `confirmed_skills` | type:feature, area:n8n |
| M5-05 | Prompt caching and cost logging | Static prefix cached; cache hits visible in `llm_calls` | type:feature, area:llm |

## M6 Evaluation & observability

| ID | Issue | Done when | Labels |
|---|---|---|---|
| M6-01 | Labelling guide and skills vocabulary | `evals/LABELING.md` and `evals/skills_vocabulary.yaml` written and frozen | type:eval |
| M6-02 | Sample and label 150 offers | Stratified sample with recorded seed; development/test split; 20 % relabelled for κ | type:eval |
| M6-03 | Extraction evaluation harness | Rules vs LLM vs hybrid; bootstrap CIs; McNemar; 3 runs per LLM configuration | type:eval, area:service |
| M6-04 | Ranking evaluation | nDCG@10 and P@10 per daily batch with CIs | type:eval |
| M6-05 | Guardrail audit | 30 CV outputs audited by hand; validator recall reported | type:eval, area:llm |
| M6-06 | WF-09 weekly report | Funnel, source health and weekly LLM cost delivered on Mondays | type:feature, area:n8n |
| M6-07 | Results report | `evals/results/REPORT.md` with tables, CIs, costs and limitations; ADR-0004 decision recorded | type:eval, type:docs |

## M7 MCP & case study

| ID | Issue | Done when | Labels |
|---|---|---|---|
| M7-01 | WF-06 MCP server | Read-only tools plus one gated action, documented with schemas | type:feature, area:n8n |
| M7-02 | MCP client connection | Connection from an MCP client documented end-to-end, including transport bridge if needed | type:docs, area:n8n |
| M7-03 | Case study | `docs/case-study.md`: problem, architecture, results, limitations, lessons learned | type:docs |
| M7-04 | Release v1.0.0 | Demo recording linked in README; tagged release with changelog | type:docs |

## Definition of Done (all issues)

- Linked to a milestone, and merged through a pull request that references the issue.
- Tests added or updated where logic changed; CI green.
- Documentation updated (README, the relevant `docs/` page, or an ADR if a decision
  changed).
- No secrets, personal data or third-party offer texts added to Git.
