"""Tests for CLI flags and output modes."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from git_recap.cli import main
from git_recap.git import Commit
from datetime import datetime


SAMPLE_COMMITS = [
    Commit(
        hash="abc12345",
        author="Kamil",
        date=datetime(2026, 3, 21, 10, 0, 0),
        message="add user auth",
        files_changed=["src/auth.py"],
    )
]


def _patch_commits(commits=None):
    return patch("git_recap.cli.get_commits", return_value=commits or SAMPLE_COMMITS)


def _patch_summarizer(text="summary text"):
    return patch("git_recap.cli.summarize", return_value=text)


def test_today_flag():
    runner = CliRunner()
    with _patch_commits(), _patch_summarizer():
        with patch("git_recap.cli.format_commits_for_prompt", return_value="commits") as mock_fmt:
            with patch("git_recap.cli.get_commits", return_value=SAMPLE_COMMITS) as mock_get:
                result = runner.invoke(main, ["--today", "--raw"])
    assert result.exit_code == 0


def test_week_flag():
    runner = CliRunner()
    with _patch_commits(), _patch_summarizer():
        result = runner.invoke(main, ["--week", "--raw"])
    assert result.exit_code == 0


def test_format_json_with_raw():
    runner = CliRunner()
    with _patch_commits():
        result = runner.invoke(main, ["--raw", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "commits" in data
    assert isinstance(data["commits"], list)


def test_format_json_with_summary():
    runner = CliRunner()
    with _patch_commits(), _patch_summarizer("this week you did X and Y"):
        result = runner.invoke(main, ["--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["summary"] == "this week you did X and Y"
    assert data["commit_count"] == 1
    assert "since" in data


def test_format_text_default():
    runner = CliRunner()
    with _patch_commits(), _patch_summarizer("recap text"):
        result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert "recap text" in result.output


def test_no_commits_exits_cleanly():
    runner = CliRunner()
    with patch("git_recap.cli.get_commits", return_value=[]):
        result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert "No commits found" in result.output


def test_output_flag_writes_file(tmp_path):
    out = tmp_path / "summary.txt"
    runner = CliRunner()
    with _patch_commits(), _patch_summarizer("my recap"):
        result = runner.invoke(main, ["--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    assert out.read_text() == "my recap"


def test_output_flag_json(tmp_path):
    out = tmp_path / "summary.json"
    runner = CliRunner()
    with _patch_commits(), _patch_summarizer("my recap"):
        result = runner.invoke(main, ["--format", "json", "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["summary"] == "my recap"


def test_format_markdown_with_summary():
    runner = CliRunner()
    with _patch_commits(), _patch_summarizer("added auth and tests"):
        result = runner.invoke(main, ["--format", "markdown"])
    assert result.exit_code == 0
    assert "## Git Recap" in result.output
    assert "added auth and tests" in result.output


def test_format_markdown_with_raw():
    runner = CliRunner()
    with _patch_commits():
        result = runner.invoke(main, ["--raw", "--format", "markdown"])
    assert result.exit_code == 0
    assert "## Commits since" in result.output
    assert "abc12345"[:7] in result.output
    assert "add user auth" in result.output


def test_format_markdown_output_file(tmp_path):
    out = tmp_path / "recap.md"
    runner = CliRunner()
    with _patch_commits(), _patch_summarizer("markdown summary"):
        result = runner.invoke(main, ["--format", "markdown", "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    assert "## Git Recap" in out.read_text()


def test_multi_repo_raw_text(tmp_path):
    repo1 = tmp_path / "alpha"
    repo2 = tmp_path / "beta"
    repo1.mkdir()
    repo2.mkdir()

    commits_a = [Commit(hash="aaa1111", author="A", date=datetime(2026, 3, 21), message="feat alpha", files_changed=[])]
    commits_b = [Commit(hash="bbb2222", author="B", date=datetime(2026, 3, 22), message="feat beta", files_changed=[])]

    runner = CliRunner()
    with patch("git_recap.cli.get_commits", side_effect=[commits_a, commits_b]):
        result = runner.invoke(main, ["--repo", str(repo1), "--repo", str(repo2), "--raw"])
    assert result.exit_code == 0
    assert "alpha" in result.output
    assert "beta" in result.output


def test_multi_repo_json_raw(tmp_path):
    repo1 = tmp_path / "alpha"
    repo2 = tmp_path / "beta"
    repo1.mkdir()
    repo2.mkdir()

    commits_a = [Commit(hash="aaa1111", author="A", date=datetime(2026, 3, 21), message="feat alpha", files_changed=[])]
    commits_b = [Commit(hash="bbb2222", author="B", date=datetime(2026, 3, 22), message="feat beta", files_changed=[])]

    runner = CliRunner()
    with patch("git_recap.cli.get_commits", side_effect=[commits_a, commits_b]):
        result = runner.invoke(main, ["--repo", str(repo1), "--repo", str(repo2), "--raw", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "repos" in data
    assert "alpha" in data["repos"]
    assert "beta" in data["repos"]


def test_multi_repo_summary(tmp_path):
    repo1 = tmp_path / "alpha"
    repo2 = tmp_path / "beta"
    repo1.mkdir()
    repo2.mkdir()

    commits_a = [Commit(hash="aaa1111", author="A", date=datetime(2026, 3, 21), message="feat alpha", files_changed=[])]
    commits_b = [Commit(hash="bbb2222", author="B", date=datetime(2026, 3, 22), message="feat beta", files_changed=[])]

    runner = CliRunner()
    with patch("git_recap.cli.get_commits", side_effect=[commits_a, commits_b]), \
         _patch_summarizer("combined recap"):
        result = runner.invoke(main, ["--repo", str(repo1), "--repo", str(repo2), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["commit_count"] == 2
    assert data["summary"] == "combined recap"
