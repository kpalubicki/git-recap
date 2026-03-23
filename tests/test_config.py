"""Tests for config loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from git_recap.config import load, _DEFAULTS


def test_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr("git_recap.config.DEFAULT_CONFIG_PATH", tmp_path / ".git-recap")
    cfg = load()
    assert cfg["model"] == _DEFAULTS["model"]
    assert cfg["since"] == _DEFAULTS["since"]
    assert cfg["author"] is None


def test_overrides_from_file(tmp_path, monkeypatch):
    config_file = tmp_path / ".git-recap"
    config_file.write_text("model=llama3.2:3b\nsince=3 days ago\nauthor=kamil\n")
    monkeypatch.setattr("git_recap.config.DEFAULT_CONFIG_PATH", config_file)

    cfg = load()
    assert cfg["model"] == "llama3.2:3b"
    assert cfg["since"] == "3 days ago"
    assert cfg["author"] == "kamil"


def test_comments_and_blank_lines_ignored(tmp_path, monkeypatch):
    config_file = tmp_path / ".git-recap"
    config_file.write_text("# this is a comment\n\nmodel=llama3.2:3b\n")
    monkeypatch.setattr("git_recap.config.DEFAULT_CONFIG_PATH", config_file)

    cfg = load()
    assert cfg["model"] == "llama3.2:3b"
    assert cfg["since"] == _DEFAULTS["since"]


def test_none_value_resolves_to_none(tmp_path, monkeypatch):
    config_file = tmp_path / ".git-recap"
    config_file.write_text("author=none\n")
    monkeypatch.setattr("git_recap.config.DEFAULT_CONFIG_PATH", config_file)

    cfg = load()
    assert cfg["author"] is None


def test_unknown_keys_ignored(tmp_path, monkeypatch):
    config_file = tmp_path / ".git-recap"
    config_file.write_text("unknown_key=value\nmodel=llama3.2:3b\n")
    monkeypatch.setattr("git_recap.config.DEFAULT_CONFIG_PATH", config_file)

    cfg = load()
    assert "unknown_key" not in cfg
    assert cfg["model"] == "llama3.2:3b"
