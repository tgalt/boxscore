"""Git-derived metadata: freshness and recently-changed lines. subprocess-only, no deps."""
from __future__ import annotations

import datetime
import re
import subprocess

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

FRESH_DAYS = 7
STALE_DAYS = 30


def _git(repo: str, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", repo, *args],
            capture_output=True, text=True, timeout=30,
        )
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def last_commit_date(repo: str, relpath: str) -> datetime.date | None:
    out = _git(repo, "log", "-1", "--format=%cs", "--", relpath).strip()
    try:
        return datetime.date.fromisoformat(out)
    except ValueError:
        return None


def freshness(date: datetime.date | None, today: datetime.date | None = None) -> str:
    """'green' <=7d, 'amber' <=30d, 'red' older, 'unknown' if no history."""
    if date is None:
        return "unknown"
    today = today or datetime.date.today()
    age = (today - date).days
    if age <= FRESH_DAYS:
        return "green"
    if age <= STALE_DAYS:
        return "amber"
    return "red"


def changed_lines(repo: str, relpath: str, days: int = 7) -> set[int]:
    """Approximate set of line numbers touched in the last `days` days.

    Hunk-level from `git log -p --since`: line numbers are as of each commit,
    so treat as an accent hint, not line-level truth (see PLAN: risks).
    """
    out = _git(repo, "log", f"--since={days} days ago", "-p",
               "--format=", "--unified=0", "--", relpath)
    lines: set[int] = set()
    for row in out.splitlines():
        m = HUNK_RE.match(row)
        if m:
            start = int(m.group(1))
            count = int(m.group(2) or "1")
            lines.update(range(start, start + max(count, 1)))
    return lines


def current_branch(repo: str) -> str:
    out = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    return out or "HEAD"
