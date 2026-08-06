#!/usr/bin/env python3
"""Block secret-bearing files from ever being committed again.

Added during Phase 0 remediation. `.env` reached this repo's public history in
3b5c6b3 and 441da0f, and `analysis_history.db` in the same commits, despite
`.gitignore` listing them -- because `.gitignore` only governs files that are not
already tracked, and `git add -f` bypasses it entirely.

This hook runs on the staged file list and cannot be bypassed except with
`--no-verify`, which is a deliberate act rather than an accident.

Exit 0 = clean, exit 1 = blocked.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Files matching these patterns must never be committed.
BLOCKED = [
    (re.compile(r"(^|/)\.env$"), "environment file with live secrets"),
    (re.compile(r"(^|/)\.env\.(?!example$)[A-Za-z0-9_.-]+$"), "environment file variant"),
    (re.compile(r"\.db$"), "database file (may contain user data / bcrypt hashes)"),
    (re.compile(r"\.sqlite3?$"), "SQLite database file"),
    (re.compile(r"(^|/)\.secrets\.toml$"), "secrets file"),
    (re.compile(r"\.(pem|key|p12|pfx)$"), "private key material"),
    (re.compile(r"(^|/)(credentials|service-account[A-Za-z0-9_.-]*)\.json$"), "cloud credentials"),
]

# Explicitly permitted despite matching above.
ALLOWED = {".env.example"}


def main(argv: list[str]) -> int:
    violations: list[tuple[str, str]] = []

    for raw in argv:
        path = Path(raw).as_posix()
        if path in ALLOWED:
            continue
        for pattern, reason in BLOCKED:
            if pattern.search(path):
                violations.append((path, reason))
                break

    if not violations:
        return 0

    print("\n  BLOCKED: refusing to commit secret-bearing files\n", file=sys.stderr)
    for path, reason in violations:
        print(f"    {path}\n        -> {reason}", file=sys.stderr)
    print(
        "\n  These belong in .env (gitignored) or a secret manager -- never in git.\n"
        "  This repo is PUBLIC; anything committed here is world-readable and is\n"
        "  scraped by automated credential harvesters within minutes.\n\n"
        "  If a file was staged by accident:\n"
        "      git restore --staged <file>\n\n"
        "  If you are certain this is safe, add it to ALLOWED in\n"
        "  scripts/block_secret_files.py -- do not use --no-verify.\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
