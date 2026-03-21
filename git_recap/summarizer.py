"""LLM summarization via Ollama."""

from __future__ import annotations

import httpx

DEFAULT_MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://localhost:11434/api/chat"

PROMPT_TEMPLATE = """\
You are summarizing a developer's recent git activity for a standup or weekly review.

Here are the commits:
{commits}

Write a short, clear summary of what was worked on. Group related changes together. \
Use plain language — no bullet points, no headers, just a few sentences. \
Don't mention commit hashes. Focus on what changed and why it matters.\
"""


def summarize(commits_text: str, model: str = DEFAULT_MODEL, ollama_url: str = OLLAMA_URL) -> str:
    """Send commits to Ollama and return a summary.

    Args:
        commits_text: Formatted commit list as plain text.
        model: Ollama model name.
        ollama_url: Ollama API endpoint.

    Returns:
        Summary string from the LLM.

    Raises:
        RuntimeError: If Ollama is unreachable or returns an error.
    """
    prompt = PROMPT_TEMPLATE.format(commits=commits_text)

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                ollama_url,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"].strip()
    except httpx.ConnectError:
        raise RuntimeError(
            "Cannot reach Ollama at localhost:11434. Is it running?\n"
            "Start it with: ollama serve"
        )
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Ollama returned an error: {e.response.text}")
