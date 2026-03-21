"""CLI entry point for git-recap."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live

from git_recap.git import get_commits, format_commits_for_prompt
from git_recap.summarizer import summarize, DEFAULT_MODEL

console = Console()


@click.command()
@click.option(
    "--repo",
    "-r",
    default=".",
    show_default=True,
    help="Path to the git repository.",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--since",
    "-s",
    default="1 week ago",
    show_default=True,
    help='Time range for commits (e.g. "1 day ago", "2026-03-01").',
)
@click.option(
    "--author",
    "-a",
    default=None,
    help="Filter commits by author name or email.",
)
@click.option(
    "--model",
    "-m",
    default=DEFAULT_MODEL,
    show_default=True,
    help="Ollama model to use for summarization.",
)
@click.option(
    "--raw",
    is_flag=True,
    default=False,
    help="Print raw commit list without LLM summary.",
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="Save the summary to a file.",
    type=click.Path(path_type=Path),
)
@click.version_option()
def main(
    repo: Path,
    since: str,
    author: str | None,
    model: str,
    raw: bool,
    output: Path | None,
) -> None:
    """Turn your git commits into a readable summary using a local LLM.

    Examples:

    \b
      git-recap                        # summarize the last week in current repo
      git-recap --since "1 day ago"    # just today
      git-recap --repo ~/projects/foo  # different repo
      git-recap --raw                  # skip the LLM, just show commits
      git-recap --output summary.txt   # save to file
    """
    try:
        commits = get_commits(repo, since=since, author=author)
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

    if not commits:
        console.print(f"[yellow]No commits found since '{since}'.[/yellow]")
        return

    commits_text = format_commits_for_prompt(commits)

    if raw:
        console.print(Panel(commits_text, title=f"[bold]{len(commits)} commits[/bold]", border_style="dim"))
        return

    console.print(f"[dim]Found {len(commits)} commit(s) since '{since}'. Summarizing...[/dim]")

    with Live(Spinner("dots", text=" Thinking..."), console=console, refresh_per_second=10):
        try:
            summary = summarize(commits_text, model=model)
        except RuntimeError as e:
            console.print(f"\n[red]Error:[/red] {e}")
            raise click.Abort()

    console.print()
    console.print(Panel(
        summary,
        title=f"[bold green]Recap[/bold green] — {len(commits)} commit(s) since '{since}'",
        border_style="green",
        padding=(1, 2),
    ))

    if output:
        output.write_text(summary, encoding="utf-8")
        console.print(f"[dim]Saved to {output}[/dim]")
