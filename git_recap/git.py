"""Git log parsing."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Commit:
    hash: str
    author: str
    date: datetime
    message: str
    files_changed: list[str]


def get_commits(
    repo_path: Path,
    since: str = "1 week ago",
    author: str | None = None,
) -> list[Commit]:
    """Return commits from the repo within the given time range.

    Args:
        repo_path: Path to the git repository root.
        since: Git date string, e.g. "1 day ago", "2026-03-01".
        author: Filter by author name or email (optional).
    """
    cmd = [
        "git", "-C", str(repo_path),
        "log",
        f"--since={since}",
        "--format=%H\t%an\t%ai\t%s",
    ]
    if author:
        cmd += [f"--author={author}"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git log failed: {result.stderr.strip()}")

    commits = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 3)
        if len(parts) < 4:
            continue
        hash_, author_name, date_str, message = parts
        try:
            date = datetime.fromisoformat(date_str)
        except ValueError:
            date = datetime.now()

        files = _get_files_changed(repo_path, hash_)
        commits.append(Commit(
            hash=hash_[:8],
            author=author_name,
            date=date,
            message=message.strip(),
            files_changed=files,
        ))

    return commits


def _get_files_changed(repo_path: Path, commit_hash: str) -> list[str]:
    """Return list of files changed in a given commit."""
    result = subprocess.run(
        ["git", "-C", str(repo_path), "diff-tree", "--no-commit-id", "-r", "--name-only", commit_hash],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [f for f in result.stdout.strip().splitlines() if f]


def format_commits_for_prompt(commits: list[Commit]) -> str:
    """Format commits into a plain-text block for the LLM prompt."""
    if not commits:
        return "No commits found."

    lines = []
    for c in commits:
        lines.append(f"- [{c.hash}] {c.message}")
        if c.files_changed:
            files_preview = ", ".join(c.files_changed[:5])
            if len(c.files_changed) > 5:
                files_preview += f" (+{len(c.files_changed) - 5} more)"
            lines.append(f"  files: {files_preview}")
    return "\n".join(lines)
