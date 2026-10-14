# ADR-0003: API-first source policy

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
The As-Is collects from four Chilean boards. Get on Board offers a documented public API.
The others are accessed through endpoints or HTML that their own sites use, under their
`robots.txt`. Publishing scraping code in a public portfolio repository creates legal and
reputational exposure if done carelessly.

## Decision
Make the **Get on Board public API the only source enabled by default**, implemented with
n8n's HTTP Request node. Other boards are **optional adapters** in `matcher-service`, off
by default, and subject to the rules in [`../data-governance.md`](../data-governance.md)
§2: `robots.txt`, rate limits, an identifiable User-Agent, no authentication bypass, and
a terms-of-use review date. Sites that forbid automated access are never collected.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Port all four sources as-is, enabled | Maximum coverage | Higher exposure in a public repository; brittle |
| **API first, adapters optional** | Defensible by default; coverage still available | Lower default coverage |
| API only | Lowest exposure | Loses most local electronics and automation offers, which appear on the other boards |

## Consequences
- The evaluation reports results per source, so coverage trade-offs are visible.
- Adapter failures are isolated per source and never abort a run.
