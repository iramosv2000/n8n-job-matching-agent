"""Normalise raw n8n workflow exports so that Git diffs show only real changes (ADR-0006).

Usage: python3 scripts/normalize_workflows.py <raw_export_dir> <workflows_dir>

- Drops volatile or instance-specific fields (timestamps, version counters, sharing).
- Drops pinned and static data, which can contain real execution data.
- Names each file after the workflow name (e.g. "WF-01 ingest-sources" -> wf-01-ingest-sources.json).
- Removes files in <workflows_dir> whose workflow no longer exists in the export.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

VOLATILE_TOP_LEVEL = {
    "createdAt",
    "updatedAt",
    "versionId",
    "activeVersionId",
    "versionCounter",
    "triggerCount",
    "shared",
    "active",
    "isArchived",
    "pinData",
    "staticData",
    "parentFolderId",
    "parentFolder",
    "homeProject",
}
VOLATILE_ANYWHERE = {"createdAt", "updatedAt"}
VOLATILE_META = {"instanceId"}


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug or "workflow"


def strip_anywhere(value):
    if isinstance(value, dict):
        return {k: strip_anywhere(v) for k, v in value.items() if k not in VOLATILE_ANYWHERE}
    if isinstance(value, list):
        return [strip_anywhere(v) for v in value]
    return value


def normalise(workflow: dict) -> dict:
    out = {k: v for k, v in workflow.items() if k not in VOLATILE_TOP_LEVEL}
    meta = out.get("meta")
    if isinstance(meta, dict):
        meta = {k: v for k, v in meta.items() if k not in VOLATILE_META}
        if meta:
            out["meta"] = meta
        else:
            out.pop("meta")
    return strip_anywhere(out)


def main(raw_dir: Path, target_dir: Path) -> int:
    target_dir.mkdir(parents=True, exist_ok=True)
    written: set[str] = set()
    for src in sorted(raw_dir.glob("*.json")):
        workflow = json.loads(src.read_text(encoding="utf-8"))
        name = f"{slugify(workflow.get('name', src.stem))}.json"
        if name in written:
            raise SystemExit(f"Two workflows normalise to the same file name: {name}")
        text = json.dumps(normalise(workflow), indent=2, ensure_ascii=False) + "\n"
        (target_dir / name).write_text(text, encoding="utf-8")
        written.add(name)
    for stale in target_dir.glob("*.json"):
        if stale.name not in written:
            stale.unlink()
            print(f"removed {stale}")
    print(f"normalised {len(written)} workflow(s) into {target_dir}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
