# ADR-0008: Source-by-source decisions after a terms-of-use review

- **Status:** Accepted
- **Date:** 2026-10-16
- **Refines:** [ADR-0003](0003-source-policy-api-first.md) (API-first source policy)

## Context
In the As-Is tool, the API-based source (Get on Board) contributed only **3 of 69** offers
scoring ≥ 70 for this candidate (4 %). The rest came from three boards accessed through their
web pages: Computrabajo 32 (46 %), Chiletrabajos 22 (32 %) and Trabajando.cl 12 (17 %).
ADR-0003 allows optional adapters only after a terms-of-use review and only where automated
access is not forbidden. The review was carried out on 2026-10-16:

| Source | robots.txt | Terms of use | Technical behaviour |
|---|---|---|---|
| Computrabajo (cl) | Not readable | Not readable | **HTTP 403 to automated clients**, including for `robots.txt` |
| Trabajando.cl | Allows `/` (a few account paths excluded) | **Prohibit aggregating, copying or duplicating site content** ([terms](https://www.trabajando.cl/terminos-y-condiciones-de-servicio)) | Public JSON endpoints |
| Chiletrabajos | Allows generic agents (blocks `Scrapy`, `/partners/`, `/ofertasmuchomas`) | No clause on automated access; **prohibit publishing or transmitting material without consent** ([terms](https://www.chiletrabajos.cl/terminos-y-condiciones)) | Server-rendered HTML with JSON-LD `JobPosting` |

## Decision
1. **Computrabajo: excluded.** It actively refuses automated clients. Working around the
   refusal (browser impersonation, header spoofing) is outside this project's policy.
2. **Trabajando.cl: excluded.** Its terms forbid exactly what an ingestion adapter does.
3. **Chiletrabajos: allowed with restrictions.**
   - Disabled by default; enabled per installation with `MATCHER_ENABLED_SOURCES=chiletrabajos`.
   - Fetched by matcher-service through `PoliteClient`, which checks robots.txt before
     every request, spaces requests by 0.8 s, backs off on 429/5xx and never retries 401/403.
     The client identifies itself with a User-Agent that includes the repository URL.
   - At most 60 new detail pages per run. Offers already stored are not re-downloaded.
   - **For personal processing only:** the content is never redistributed and **never sent
     to external LLM APIs**. `GET /sources` exposes `external_llm_allowed: false`, and the
     LLM router (M3-07) must route its text to the local model only.
4. **Coverage compensation without automated collection:**
   - **Manual intake** (new issue, M4): the candidate forwards an offer seen on any board to
     the Telegram bot, and it enters the same pipeline. This is personal use of content the
     candidate accessed directly.
   - **Search links** to excluded boards in the daily digest (M4-02), as the As-Is did for
     LinkedIn.

## Alternatives considered
| Option | Why not |
|---|---|
| Port all As-Is adapters as they were | Conflicts with Trabajando.cl's terms and Computrabajo's refusal; unacceptable in a public portfolio |
| API only, no optional sources | Defensible, but loses ~96 % of the relevant offers in the As-Is data |
| Impersonate a browser for Computrabajo | Circumvents an access control; excluded by policy |

## Consequences
- Expected automated coverage of the relevant offers in the As-Is data rises from ~4 % (API
  only) to ~36 % (API plus Chiletrabajos). Manual intake covers the rest on demand.
- This is the project's application of its own policy, **not legal advice**. Terms can
  change, so each review date is exposed by `GET /sources` and must be renewed before
  enabling a source on a new installation or after six months.
- The As-Is tool, which is personal and not published, still contains adapters for the
  excluded boards. That code must not be published.
