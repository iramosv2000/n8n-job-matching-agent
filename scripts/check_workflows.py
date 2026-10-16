"""Validate exported n8n workflows before they reach Git (used by pre-commit and CI).

Usage: python3 scripts/check_workflows.py <file-or-directory> [...]

Fails when a workflow is not valid JSON, lacks the expected structure, carries pinned or
static execution data, embeds anything other than credential references, or contains a
string that looks like a secret.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SECRET_PATTERNS = {
    "Google API key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "Anthropic API key": re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    "OpenAI-style API key": re.compile(r"\bsk-[A-Za-z0-9]{32,}"),
    "Telegram bot token": re.compile(r"(?<!\d)\d{8,10}:[A-Za-z0-9_\-]{35}(?![A-Za-z0-9_\-])"),
    "JSON Web Token": re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "PostgreSQL URL with password": re.compile(r"postgres(?:ql)?://[^:\s/]+:[^@\s]+@"),
}


def check_workflow(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    try:
        workflow = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]

    if not isinstance(workflow, dict):
        return ["top level must be a JSON object"]
    for key, kind in (("name", str), ("nodes", list), ("connections", dict)):
        if not isinstance(workflow.get(key), kind):
            errors.append(f"missing or invalid '{key}'")
    for key in ("pinData", "staticData"):
        if workflow.get(key):
            errors.append(f"'{key}' must be empty (may contain execution data); re-export with the script")

    for node in workflow.get("nodes") or []:
        for cred_type, ref in (node.get("credentials") or {}).items():
            if not isinstance(ref, dict) or set(ref) - {"id", "name"}:
                errors.append(f"node '{node.get('name')}': credential '{cred_type}' is not a bare reference")

    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"contains what looks like a {label}")
    return errors


def iter_files(args: list[str]):
    for arg in args:
        path = Path(arg)
        if path.is_dir():
            yield from sorted(path.glob("*.json"))
        elif path.suffix == ".json":
            yield path


def duplicate_ids(files: list[Path]) -> list[str]:
    """Two files with the same workflow id would overwrite each other on import."""
    seen: dict[str, Path] = {}
    errors = []
    for path in files:
        try:
            workflow_id = json.loads(path.read_text(encoding="utf-8")).get("id")
        except (json.JSONDecodeError, AttributeError):
            continue
        if workflow_id and workflow_id in seen:
            errors.append(f"{path}: workflow id {workflow_id!r} also used by {seen[workflow_id]}")
        elif workflow_id:
            seen[workflow_id] = path
    return errors


def main(args: list[str]) -> int:
    failed = 0
    files = list(iter_files(args))
    for path in files:
        for error in check_workflow(path):
            print(f"{path}: {error}")
            failed += 1
    for error in duplicate_ids(files):
        print(error)
        failed += 1
    if failed:
        print(f"{failed} problem(s) found in workflow exports")
        return 1
    print(f"{len(files)} workflow file(s) OK")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1:]))
