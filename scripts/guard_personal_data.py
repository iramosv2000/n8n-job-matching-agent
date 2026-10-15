"""Pre-commit guard: block personal data and collected third-party data from entering Git.

Usage: python3 scripts/guard_personal_data.py <file> [...]

Checks, for each staged file:
1. Forbidden paths: the master CV/protocol, real profiles, databases, collected offers.
2. Generic personal identifiers: Chilean phone numbers, Chilean RUT, e-mail addresses
   outside an allow-list of placeholder domains.
3. An optional local deny-list with the author's own identifiers, kept outside the repo:
   a text file (one literal per line) at $PERSONAL_DATA_DENYLIST or
   ~/.config/job-matcher/denylist.txt. It is never committed.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

FORBIDDEN_PATHS = [
    re.compile(r"CONFIGURACION_AGENTE_EMPLEO", re.IGNORECASE),
    re.compile(r"(^|/)profiles/(?!README\.md$|example/)"),
    re.compile(r"\.(sqlite3?|db)$"),
    re.compile(r"(^|/)ofertas[^/]*\.csv$"),
    re.compile(r"(^|/)\.env$"),
]
PHONE_CL = re.compile(r"(?<!\d)(?:\+?56[\s.-]?)9[\s.-]?\d{4}[\s.-]?\d{4}(?!\d)")
RUT_CL = re.compile(r"(?<![\d.])\d{1,2}\.\d{3}\.\d{3}-[\dkK](?![\w])")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}")
ALLOWED_EMAIL_DOMAINS = (
    "example.com",
    "example.org",
    "example.net",
    "users.noreply.github.com",
    "noreply.anthropic.com",
    "anthropic.com",
)
DEFAULT_DENYLIST = Path.home() / ".config" / "job-matcher" / "denylist.txt"


def load_denylist() -> list[str]:
    path = Path(os.environ.get("PERSONAL_DATA_DENYLIST", DEFAULT_DENYLIST))
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip().lower() for line in lines if line.strip() and not line.startswith("#")]


def check_file(path: Path, denylist: list[str]) -> list[str]:
    posix = path.as_posix()
    problems = [f"forbidden path ({p.pattern})" for p in FORBIDDEN_PATHS if p.search(posix)]
    if problems:
        return problems
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError):
        return []
    if PHONE_CL.search(text):
        problems.append("contains a Chilean phone number")
    if RUT_CL.search(text):
        problems.append("contains a Chilean RUT")
    for match in EMAIL.finditer(text):
        address = match.group(0).lower()
        if not address.endswith(ALLOWED_EMAIL_DOMAINS):
            problems.append(f"contains an e-mail address ({address.split('@')[1]})")
    lowered = text.lower()
    problems += ["contains an entry of the local deny-list" for item in denylist if item in lowered][:1]
    return problems


def main(args: list[str]) -> int:
    denylist = load_denylist()
    failed = 0
    for arg in args:
        for problem in check_file(Path(arg), denylist):
            print(f"{arg}: {problem}")
            failed += 1
    if failed:
        print("Personal or collected data must not be committed (docs/data-governance.md).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
