"""Tests for git log parsing."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from git_recap.git import get_commits, format_commits_for_prompt, Commit
from datetime import datetime


SAMPLE_LOG = "\n".join([
    "abc12345\tKamil\t2026-03-21 10:00:00+01:00\tadd user auth",
    "def67890\tKamil\t2026-03-20 15:30:00+01:00\tfix login redirect",
])

SAMPLE_FILES = "src/auth.py\nsrc/views.py"


def _mock_run(cmd, **kwargs):
    mock = MagicMock()
    mock.returncode = 0
    if "log" in cmd:
        mock.stdout = SAMPLE_LOG
    elif "diff-tree" in cmd:
        mock.stdout = SAMPLE_FILES
    else:
        mock.stdout = ""
    mock.stderr = ""
    return mock


def test_get_commits_returns_list(tmp_path):
    with patch("subprocess.run", side_effect=_mock_run):
        commits = get_commits(tmp_path, since="1 week ago")

    assert len(commits) == 2
    assert commits[0].hash == "abc12345"
    assert commits[0].message == "add user auth"
    assert commits[0].author == "Kamil"


def test_get_commits_parses_files(tmp_path):
    with patch("subprocess.run", side_effect=_mock_run):
        commits = get_commits(tmp_path)

    assert "src/auth.py" in commits[0].files_changed
    assert "src/views.py" in commits[0].files_changed


def test_get_commits_raises_on_git_error(tmp_path):
    mock = MagicMock()
    mock.returncode = 128
    mock.stderr = "not a git repository"
    with patch("subprocess.run", return_value=mock):
        with pytest.raises(RuntimeError, match="git log failed"):
            get_commits(tmp_path)


def test_get_commits_empty_repo(tmp_path):
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = ""
    mock.stderr = ""
    with patch("subprocess.run", return_value=mock):
        commits = get_commits(tmp_path)
    assert commits == []


def test_format_commits_basic():
    commits = [
        Commit(
            hash="abc12345",
            author="Kamil",
            date=datetime.now(),
            message="add user auth",
            files_changed=["src/auth.py"],
        )
    ]
    result = format_commits_for_prompt(commits)
    assert "abc12345" in result
    assert "add user auth" in result
    assert "src/auth.py" in result


def test_format_commits_empty():
    result = format_commits_for_prompt([])
    assert result == "No commits found."


def test_format_commits_truncates_long_file_list():
    commits = [
        Commit(
            hash="abc12345",
            author="Kamil",
            date=datetime.now(),
            message="big refactor",
            files_changed=[f"src/file{i}.py" for i in range(10)],
        )
    ]
    result = format_commits_for_prompt(commits)
    assert "+5 more" in result
