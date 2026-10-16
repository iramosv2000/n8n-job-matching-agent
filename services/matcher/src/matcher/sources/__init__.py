"""Source registry and per-source policy (ADR-0003, ADR-0008).

Optional sources are fetched by matcher-service and are disabled unless listed in the
MATCHER_ENABLED_SOURCES environment variable (comma-separated). Get on Board is fetched by n8n
through its documented public API and is always enabled.
"""

import os

from matcher.models import SourceInfo

POLICIES = {
    "getonbrd": {
        "fetched_by": "n8n",
        "external_llm_allowed": True,
        "terms_reviewed": "2026-10-16",
        "terms_url": "https://www.getonbrd.com/help/que-puedo-hacer-con-la-api-de-get-on-board",
    },
    "chiletrabajos": {
        "fetched_by": "matcher",
        "external_llm_allowed": False,
        "terms_reviewed": "2026-10-16",
        "terms_url": "https://www.chiletrabajos.cl/terminos-y-condiciones",
    },
}


def enabled_sources() -> set[str]:
    configured = os.environ.get("MATCHER_ENABLED_SOURCES", "")
    return {"getonbrd"} | {s.strip() for s in configured.split(",") if s.strip() in POLICIES}


def source_info() -> list[SourceInfo]:
    enabled = enabled_sources()
    return [SourceInfo(name=name, enabled=name in enabled, **policy) for name, policy in POLICIES.items()]
