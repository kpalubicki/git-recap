"""Tests for the summarizer module."""

from unittest.mock import patch, MagicMock

import httpx
import pytest

from git_recap.summarizer import summarize


FAKE_SUMMARY = "Worked on user authentication and fixed a login redirect bug."


def _mock_post_success(*args, **kwargs):
    mock = MagicMock()
    mock.status_code = 200
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {
        "message": {"content": FAKE_SUMMARY}
    }
    return mock


def test_summarize_returns_text():
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = _mock_post_success
        mock_client_cls.return_value = mock_client

        result = summarize("- [abc] add auth\n- [def] fix redirect")

    assert result == FAKE_SUMMARY


def test_summarize_raises_on_connection_error():
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(side_effect=httpx.ConnectError("refused"))
        mock_client_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="Cannot reach Ollama"):
            summarize("some commits")


def test_summarize_raises_on_http_error():
    with patch("httpx.Client") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "model not found"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(
            side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=mock_response)
        )
        mock_client_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="Ollama returned an error"):
            summarize("some commits")


def test_summarize_strips_whitespace():
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"message": {"content": "  summary with spaces  "}}),
        ))
        mock_client_cls.return_value = mock_client

        result = summarize("commits")

    assert result == "summary with spaces"
